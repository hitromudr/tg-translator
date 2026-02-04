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
    is_voice = False

    # Check if this is a voice transcription message
    # We used "🎤 <i>transcription</i>" format in handle_voice
    if bot_message.text and "🎤" in bot_message.text:
        is_voice = True
        # Extract text, removing the microphone icon.
        # Note: bot_message.text gives plain text, ignoring HTML tags.
        text_to_translate = bot_message.text.replace("🎤", "").strip()
    else:
        # Standard text message case (placeholder "Translate?")
        original_message = bot_message.reply_to_message
        if not original_message or not original_message.text:
            await bot_message.edit_text("❌ Original message not found or has no text.")
            return
        text_to_translate = original_message.text

    # Perform translation
    translator_service = context.bot_data["translator_service"]
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
        # Keep the original transcription (using text_html to preserve existing formatting like italics)
        # We append the translation below it.
        final_text = f"{bot_message.text_html}\n{spoiler_text}"

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
        await bot_message.edit_text(
            f"{bot_message.text}\n\nTranslation: {translation}",
            reply_markup=reply_markup,
        )
