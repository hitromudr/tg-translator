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

from .db import Database

logger = logging.getLogger(__name__)


class TranslatorService:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db
        # Executor for running synchronous translation in async context
        self._executor = ThreadPoolExecutor(max_workers=4)

    def get_supported_languages(self) -> dict[str, str]:
        """Return a dictionary of supported languages (name -> code)."""
        return cast(
            dict[str, str], GoogleTranslator().get_supported_languages(as_dict=True)
        )

    def normalize_language_code(self, lang_input: str) -> Optional[str]:
        """
        Try to find a valid language code from input (code or name).
        Case-insensitive.
        Returns the canonical code (e.g. 'zh-CN') or None.
        """
        if not lang_input:
            return None

        lang_input = lang_input.strip().lower()

        # Common aliases for user convenience
        aliases = {
            "cn": "zh-CN",
            "ua": "uk",
            "cz": "cs",
            "jp": "ja",
            "kr": "ko",
            "rs": "sr",
            "by": "be",
        }
        if lang_input in aliases:
            lang_input = aliases[lang_input].lower()

        supported = self.get_supported_languages()

        # 1. Check against codes (values) case-insensitively
        for code in supported.values():
            if code.lower() == lang_input:
                return code

        # 2. Check against names (keys) case-insensitively
        # deep_translator keys are typically lowercase
        if lang_input in supported:
            return supported[lang_input]

        return None

    def is_language_supported(self, lang_code: str) -> bool:
        """Check if a language code (or name) is supported."""
        return self.normalize_language_code(lang_code) is not None

    def _translate_sync(
        self,
        text: str,
        primary_lang: str = "ru",
        secondary_lang: str = "en",
        original_text: Optional[str] = None,
    ) -> Optional[str]:
        """
        Synchronous translation logic with dynamic language support.
        """
        try:
            # Determine direction based on original text (to handle dictionary substitutions)
            sample_text = original_text if original_text else text

            # Strategy:
            # 1. Try translating sample to Primary.
            # 2. If it changes, Source is likely Secondary (or Third). Target -> Primary.
            # 3. If it stays same, Source is likely Primary. Target -> Secondary.

            to_primary = GoogleTranslator(source="auto", target=primary_lang)
            res_prim = cast(str, to_primary.translate(sample_text))

            is_source_primary = False
            if res_prim and res_prim.lower().strip() == sample_text.lower().strip():
                is_source_primary = True

            target_lang = secondary_lang if is_source_primary else primary_lang

            # Optimization: If target is Primary and we haven't modified text, return result
            if target_lang == primary_lang and text == sample_text:
                return res_prim

            # Translate actual text to determined target
            translator = GoogleTranslator(source="auto", target=target_lang)
            return cast(str, translator.translate(text))

        except Exception as e:
            logger.error(f"Translation service error: {e}")
            return None

    def _apply_custom_dictionary(
        self, text: str, chat_id: Optional[int], lang_pair: str = "ru-en"
    ) -> str:
        if not self.db or chat_id is None:
            return text

        terms = self.db.get_terms(chat_id, lang_pair)
        if not terms:
            return text

        # Sort by length of source term (descending) to match longest phrases first
        terms.sort(key=lambda x: len(x[0]), reverse=True)

        processed_text = text
        for source, target in terms:
            # Create a regex for case-insensitive replacement with word boundaries
            # escaping source to handle special regex chars
            try:
                pattern = re.compile(r"\b" + re.escape(source) + r"\b", re.IGNORECASE)
                processed_text = pattern.sub(target, processed_text)
            except Exception as e:
                logger.error(f"Regex error for term '{source}': {e}")

        return processed_text

    async def translate_message(
        self, text: str, chat_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Asynchronously translates text using chat-specific language settings.
        """
        if not text or not text.strip():
            return None

        # Defaults
        primary = "ru"
        secondary = "en"

        if self.db and chat_id:
            primary, secondary = self.db.get_languages(chat_id)

        # Construct language pair string for dictionary lookup (alphabetical order)
        langs = sorted([primary, secondary])
        lang_pair = f"{langs[0]}-{langs[1]}"

        # Apply dictionary substitutions before translation
        text_to_translate = self._apply_custom_dictionary(text, chat_id, lang_pair)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self._translate_sync,
            text_to_translate,
            primary,
            secondary,
            text,  # original_text
        )

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
