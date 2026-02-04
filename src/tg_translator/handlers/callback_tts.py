import logging
import os
import re

from telegram import Message, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def tts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle TTS button click."""
    query = update.callback_query
    if not query:
        return

    # Providing feedback immediately to prevent spam clicking
    await query.answer("🔊 Generating audio...")

    message = query.message
    if not message or not isinstance(message, Message):
        return

    text = message.text
    if not text:
        return

    # Clean up text for TTS:
    # 1. Remove microphone emoji if present (from voice messages)
    # 2. If multiple lines (voice msg with transcription + translation), take the last one (translation)
    text = text.replace("🎤", "").strip()
    if "\n" in text:
        text = text.split("\n")[-1].strip()

    chat_id = message.chat_id

    # Retrieve dependencies from context
    db = context.bot_data["db"]
    translator_service = context.bot_data["translator_service"]

    l1, l2 = db.get_languages(chat_id)
    gender = db.get_voice_gender(chat_id)

    # Simple heuristic for language detection to decide which voice to use
    lang = l2
    has_cyrillic = bool(re.search(r"[а-яА-ЯёЁ]", text))

    if has_cyrillic:
        # If any of the configured languages is typically Cyrillic, use it
        cyrillic_langs = ["ru", "uk", "sr", "be", "bg", "mk", "kk", "ky", "tg"]
        if l1 in cyrillic_langs:
            lang = l1
        elif l2 in cyrillic_langs:
            lang = l2
        else:
            lang = "ru"  # Default fallback
    else:
        # Non-cyrillic: favor English if present, otherwise secondary
        if l1 == "en":
            lang = "en"
        elif l2 == "en":
            lang = "en"
        # else keep default l2

    try:
        file_path = await translator_service.generate_audio(text, lang, gender)
        if file_path:
            await message.reply_voice(voice=open(file_path, "rb"))
            os.remove(file_path)
    except Exception as e:
        logger.error(f"TTS error: {e}")
