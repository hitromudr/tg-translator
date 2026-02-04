import html
import logging
import os
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming text messages.
    Translates the message and replies to the user.
    """
    if not update.message or not update.message.text or not update.effective_chat:
        return

    # Check chat mode
    db = context.bot_data["db"]
    mode = db.get_mode(update.effective_chat.id)
    if mode == "off" or mode == "manual":
        return

    original_text = update.message.text

    # Ignore messages without text content (emojis-only, punctuation-only)
    if not re.search(r"\w", original_text):
        return

    if mode == "interactive":
        l1, l2 = db.get_languages(update.effective_chat.id)
        # Heuristic: if Cyrillic is present, assume source is l1 (e.g. RU) -> target is l2 (EN)
        has_cyrillic = bool(re.search(r"[а-яА-ЯёЁ]", original_text))
        target_lang = l2 if has_cyrillic else l1
        label = f"🌐 to {target_lang.upper()}"

        keyboard = [[InlineKeyboardButton(label, callback_data="translate_this")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        sent_msg = await update.message.reply_text("...", reply_markup=reply_markup)

        # Save text to DB so callback can retrieve it even if original is deleted/inaccessible
        key = f"{update.effective_chat.id}:{sent_msg.message_id}"
        db.add_transcription(key, original_text)
        return

    user = update.message.from_user
    if user:
        username = user.username or user.first_name
    else:
        username = "Unknown"

    logger.info(f"Received message from {username}: {original_text[:50]}...")

    translator_service = context.bot_data["translator_service"]

    translation = await translator_service.translate_message(
        original_text, update.effective_chat.id
    )

    if translation and translation != original_text:
        # We reply to the original message with the translation
        safe_translation = html.escape(translation)

        # TTS Button
        keyboard = [[InlineKeyboardButton("🔊 Speak", callback_data="speak")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            safe_translation, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
        logger.info(f"Sent translation: {translation[:50]}...")
    else:
        logger.debug("No translation performed or translation identical to source.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming voice messages.
    Transcribes audio, translates text, and replies.
    """
    if not update.message or not update.message.voice or not update.effective_chat:
        return

    # Check chat mode
    db = context.bot_data["db"]
    mode = db.get_mode(update.effective_chat.id)
    if mode == "off" or mode == "manual":
        return

    user = update.message.from_user
    if user:
        username = user.username or user.first_name
    else:
        username = "Unknown"
    logger.info(f"Received voice message from {username}")

    translator_service = context.bot_data["translator_service"]

    try:
        voice_file = await update.message.voice.get_file()

        # Create temp directory if not exists
        os.makedirs("tmp", exist_ok=True)

        file_path = f"tmp/voice_{update.message.voice.file_unique_id}.ogg"
        await voice_file.download_to_drive(file_path)

        transcription = await translator_service.transcribe_audio(file_path)

        if transcription:
            logger.info(f"Transcribed text: {transcription[:50]}...")

            if mode == "interactive":
                l1, l2 = db.get_languages(update.effective_chat.id)
                label = f"🌐 {l1.upper()}/{l2.upper()}"

                # Voice case: Two buttons
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📝 Text", callback_data="transcribe_this"
                        ),
                        InlineKeyboardButton(label, callback_data="translate_this"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Send placeholder
                sent_msg = await update.message.reply_text(
                    "...",
                    reply_markup=reply_markup,
                )

                # Store transcription in DB linked to this message ID
                key = f"{update.effective_chat.id}:{sent_msg.message_id}"
                db.add_transcription(key, transcription)

                logger.info(
                    "Sent transcription placeholder for voice message (interactive)."
                )
                return

            translation = await translator_service.translate_message(
                transcription, update.effective_chat.id
            )

            response_parts = []
            response_parts.append(f"🎤 <i>{html.escape(transcription)}</i>")

            if translation and translation.lower() != transcription.lower():
                safe_translation = html.escape(translation)
                response_parts.append(safe_translation)

            # TTS Button
            keyboard = [[InlineKeyboardButton("🔊 Speak", callback_data="speak")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "\n".join(response_parts),
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
            logger.info("Sent transcription/translation for voice message.")
        else:
            logger.info("Could not transcribe voice message.")

    except Exception as e:
        logger.error(f"Error handling voice message: {e}")
    finally:
        # Clean up the downloaded ogg file
        if "file_path" in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
