import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, cast

from deep_translator import GoogleTranslator  # type: ignore

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
                return cast(str, self._to_en.translate(text))
            else:
                # Source does not contain Cyrillic (likely English/Latin) -> Translate to Russian
                return cast(str, self._to_ru.translate(text))
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

    def shutdown(self) -> None:
        """Cleanup resources."""
        self._executor.shutdown(wait=True)
