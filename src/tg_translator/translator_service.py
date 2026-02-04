import asyncio
import logging
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, cast

import soundfile as sf  # type: ignore
import torch  # type: ignore
import torchaudio  # type: ignore
from deep_translator import GoogleTranslator  # type: ignore
from faster_whisper import WhisperModel  # type: ignore
from gtts import gTTS  # type: ignore
from pydub import AudioSegment  # type: ignore

from .db import Database

logger = logging.getLogger(__name__)


class TranslatorService:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db
        # Executor for running synchronous translation in async context
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.whisper_model: Optional[WhisperModel] = None
        # Cache for Silero TTS models: {model_id: model_object}
        self.silero_models: Dict[str, Any] = {}

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

            # Heuristic: If primary lang implies Cyrillic, and text has Cyrillic -> Source IS Primary.
            # This avoids API call and fixes the dictionary bug.
            cyrillic_langs = {"ru", "uk", "be", "sr", "bg", "mk", "kk", "ky", "tg"}
            is_source_primary = None

            if primary_lang in cyrillic_langs and bool(
                re.search(r"[а-яА-ЯёЁ]", sample_text)
            ):
                is_source_primary = True

            if is_source_primary is None:
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

    def _generate_audio_silero_sync(
        self, text: str, lang: str, gender: str = "male"
    ) -> Optional[str]:
        """
        Generate audio using Silero TTS (high quality).
        Returns path to generated file or None if lang not supported/error.
        """
        try:
            # Map lang to Silero model params
            # We use snakers4/silero-models repository logic
            lang_code = lang.lower()
            speaker = None
            model_id = None

            if lang_code == "ru":
                # v4_ru supports: aidar (male), kseniya (female), eugene (male), baya (female)
                model_id = "v4_ru"
                if gender == "female":
                    speaker = "kseniya"
                else:
                    speaker = "aidar"
            elif lang_code in ["uk", "ua"]:
                # v4_ua supports: mykyta (male).
                lang_code = "ua"  # Silero uses 'ua' code
                model_id = "v4_ua"
                # Fallback to male if female not available in standard package
                speaker = "mykyta"
            elif lang_code == "en":
                # v3_en supports: en_0 .. en_117
                model_id = "v3_en"
                if gender == "female":
                    speaker = "en_1"  # Example female voice
                else:
                    speaker = "en_2"  # Distinct male voice
            else:
                # Language not supported by our Silero config, fallback to gTTS
                return None

            device = torch.device("cpu")

            # Lazy load model
            if model_id not in self.silero_models:
                logger.info(f"Loading Silero TTS model: {model_id} ({lang_code})")
                model, _ = torch.hub.load(
                    repo_or_dir="snakers4/silero-models",
                    model="silero_tts",
                    language=lang_code,
                    speaker=model_id,
                )
                model.to(device)
                self.silero_models[model_id] = model

            model = self.silero_models[model_id]

            # Generate audio (Tensor)
            # sample_rate 48000 is standard for v4 models
            sample_rate = 48000
            audio = model.apply_tts(
                text=text,
                speaker=speaker,
                sample_rate=sample_rate,
                put_accent=True,
                put_yo=True,
            )

            # Save to temporary WAV file
            os.makedirs("tmp", exist_ok=True)
            wav_filename = f"tmp/tts_silero_{uuid.uuid4()}.wav"

            # Audio is 1D tensor [samples]. Save using soundfile (numpy array).
            sf.write(wav_filename, audio.numpy(), sample_rate)

            # Convert to MP3 using pydub for compatibility/size
            mp3_filename = wav_filename.replace(".wav", ".mp3")
            AudioSegment.from_wav(wav_filename).export(mp3_filename, format="mp3")

            # Cleanup WAV
            if os.path.exists(wav_filename):
                os.remove(wav_filename)

            return mp3_filename

        except Exception as e:
            logger.error(f"Silero TTS error for {lang}: {e}")
            return None

    def _generate_audio_sync(
        self, text: str, lang: str, gender: str = "male"
    ) -> Optional[str]:
        """
        Synchronous audio generation.
        Tries Silero TTS first, falls back to gTTS.
        """
        # Try Silero first
        silero_path = self._generate_audio_silero_sync(text, lang, gender)
        if silero_path:
            return silero_path

        # Fallback to gTTS
        try:
            filename = f"tmp/tts_gtts_{uuid.uuid4()}.mp3"
            os.makedirs("tmp", exist_ok=True)

            tts = gTTS(text=text, lang=lang)
            tts.save(filename)
            return filename
        except Exception as e:
            logger.error(f"gTTS generation error: {e}")
            return None

    async def generate_audio(
        self, text: str, lang: str, gender: str = "male"
    ) -> Optional[str]:
        """
        Asynchronously generate audio for the given text.
        Returns path to the generated MP3 file.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._generate_audio_sync, text, lang, gender
        )

    def _get_whisper_model(self) -> WhisperModel:
        """
        Lazy load the Whisper model on first use.
        Configured for 4-core server hosting LiveKit alongside.
        cpu_threads=2 ensures we don't starve other processes.
        """
        if self.whisper_model is None:
            logger.info("Loading Whisper model (small, int8)...")
            self.whisper_model = WhisperModel(
                "small", device="cpu", compute_type="int8", cpu_threads=2
            )
        return self.whisper_model

    def _transcribe_sync(self, file_path: str) -> Optional[str]:
        """
        Synchronous transcription logic using Faster-Whisper.
        Directly accepts OGG (Telegram voice) via ffmpeg backend.
        """
        try:
            model = self._get_whisper_model()
            # beam_size=5 provides better accuracy than greedy search
            segments, info = model.transcribe(file_path, beam_size=5)

            # Segments is a generator, iteration triggers processing
            text = " ".join([segment.text for segment in segments]).strip()
            if not text:
                return None
            return text
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return None

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
