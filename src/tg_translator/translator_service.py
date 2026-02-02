import asyncio
import logging
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, cast

import speech_recognition as sr  # type: ignore
from deep_translator import GoogleTranslator  # type: ignore
from pydub import AudioSegment  # type: ignore

logger = logging.getLogger(__name__)


class TranslatorService:
    def __init__(self) -> None:
        # We initialize translators for specific directions.
        # Deep Translator uses 'auto' for source detection which is convenient.
        self._to_en = GoogleTranslator(source="auto", target="en")
        self._to_ru = GoogleTranslator(source="auto", target="ru")

        # Executor for running synchronous translation in async context
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _is_cyrillic(self, text: str) -> bool:
        """
        Check if the text contains Cyrillic characters.
        Used as a simple heuristic to determine if the source is likely Russian.
        """
        return bool(re.search(r"[а-яА-ЯёЁ]", text))

    def _translate_sync(self, text: str) -> Optional[str]:
        """
        Synchronous translation logic to be run in an executor.
        """
        try:
            if self._is_cyrillic(text):
                # Source contains Cyrillic -> Translate to English
                # Note: deep-translator handles 'auto' source well,
                # but we decide direction based on content presence.
                translation = cast(str, self._to_en.translate(text))
                # If translation is identical to source (e.g. mixed languages), try the other direction
                if translation and translation.lower().strip() == text.lower().strip():
                    translation = cast(str, self._to_ru.translate(text))
                return translation
            else:
                # Source does not contain Cyrillic (likely English/Latin) -> Translate to Russian
                translation = cast(str, self._to_ru.translate(text))
                # If translation is identical to source, try the other direction
                if translation and translation.lower().strip() == text.lower().strip():
                    translation = cast(str, self._to_en.translate(text))
                return translation
        except Exception as e:
            logger.error(f"Translation service error: {e}")
            return None

    async def translate_message(self, text: str) -> Optional[str]:
        """
        Asynchronously translates text.

        Logic:
        - If text contains Cyrillic characters -> Translate to English.
        - Otherwise -> Translate to Russian.
        """
        if not text or not text.strip():
            return None

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._translate_sync, text)

    def _transcribe_sync(self, file_path: str) -> Optional[str]:
        """
        Synchronous transcription logic.
        """
        wav_path = f"{file_path}_{uuid.uuid4()}.wav"
        try:
            # Convert audio (likely OGG) to WAV for SpeechRecognition
            sound = AudioSegment.from_file(file_path)

            # Add 500ms silence to prevent cut-offs at the end
            sound += AudioSegment.silent(duration=500)

            sound.export(wav_path, format="wav")

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)
                # Try recognizing as Russian first
                try:
                    text = recognizer.recognize_google(audio_data, language="ru-RU")
                    return cast(str, text)
                except sr.UnknownValueError:
                    # If failed, try English
                    try:
                        text = recognizer.recognize_google(audio_data, language="en-US")
                        return cast(str, text)
                    except sr.UnknownValueError:
                        logger.debug("Speech recognition could not understand audio")
                        return None
                except sr.RequestError as e:
                    logger.error(f"Google Speech Recognition service error: {e}")
                    return None
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
        finally:
            if os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except OSError:
                    pass

    async def transcribe_audio(self, file_path: str) -> Optional[str]:
        """
        Asynchronously transcribe audio file.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._transcribe_sync, file_path
        )

    def shutdown(self) -> None:
        """Cleanup resources."""
        self._executor.shutdown(wait=True)
