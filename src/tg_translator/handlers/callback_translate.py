import html
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def translate_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the 'Translate' button click in interactive mode.
    Reads text from reply_to_message (or current message for voice) and edits the message with translation.
    """
    query = update.callback_query
    if not query:
        return

    await query.answer()

    bot_message = query.message
    if not bot_message or not isinstance(bot_message, Message):
        return

    text_to_translate = ""
    transcription_text = ""
    is_voice = False

    # Access dependencies
    db = context.bot_data["db"]
    translator_service = context.bot_data["translator_service"]

    # Check if this is a voice transcription message placeholder
    # Clean up zero-width space if present
    clean_msg_text = (
        bot_message.text.replace("\u200b", "").strip() if bot_message.text else ""
    )

    if "🎤" in clean_msg_text:
        is_voice = True

        # Try to fetch transcription from DB (Lazy Load)
        key = f"{bot_message.chat_id}:{bot_message.message_id}"
        transcription_text = db.get_transcription(key)

        if transcription_text:
            text_to_translate = transcription_text
        else:
            # Fallback: Extract text from message if present (legacy support)
            # Remove "Voice message" placeholder text if present
            cleaned_text = (
                clean_msg_text.replace("🎤", "").replace("Voice message", "").strip()
            )
            if cleaned_text:
                text_to_translate = cleaned_text
                transcription_text = cleaned_text
            else:
                await bot_message.edit_text("❌ Transcription expired or not found.")
                return
    else:
        # Standard text message case (placeholder "Translate?", "📝", "🌐")
        original_message = bot_message.reply_to_message
        if not original_message or not original_message.text:
            await bot_message.edit_text("❌ Original message not found or has no text.")
            return
        text_to_translate = original_message.text

    # Perform translation
    translation = await translator_service.translate_message(
        text_to_translate, bot_message.chat_id
    )

    if not translation:
        await bot_message.edit_text("❌ Translation failed.")
        return

    # Format output
    safe_translation = html.escape(translation)
    spoiler_text = f'<span class="tg-spoiler">{safe_translation}</span>'

    final_text = spoiler_text
    if is_voice:
        # Show transcription AND translation
        # Since we fetched raw text from DB, we need to escape it for HTML
        safe_transcription = html.escape(transcription_text)
        final_text = f"🎤 <i>{safe_transcription}</i>\n{spoiler_text}"

    # Add Speak button for the translated text
    keyboard = [[InlineKeyboardButton("🔊 Speak", callback_data="speak")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await bot_message.edit_text(
            final_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message with translation: {e}")
        # In case of formatting error, fallback to plain text
        # Use original text for fallback
        await bot_message.edit_text(
            f"{text_to_translate}\n\nTranslation: {translation}",
            reply_markup=reply_markup,
        )
