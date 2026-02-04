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
    Handle 'Text' (transcribe) and 'Translate' buttons in interactive mode.
    """
    query = update.callback_query
    if not query:
        return

    await query.answer()

    bot_message = query.message
    if not bot_message or not isinstance(bot_message, Message):
        return

    action = query.data  # transcribe_this | translate_this
    text_to_use = ""
    is_voice = False

    # Access dependencies
    db = context.bot_data["db"]
    translator_service = context.bot_data["translator_service"]

    # 1. Try to find text in DB (Voice case)
    key = f"{bot_message.chat_id}:{bot_message.message_id}"
    transcription_text = db.get_transcription(key)

    if transcription_text:
        text_to_use = transcription_text
        is_voice = True
    else:
        # 2. Try to extract from message itself (if already transcribed)
        clean_msg_text = (
            bot_message.text.replace("\u200b", "").strip() if bot_message.text else ""
        )
        if "🎤" in clean_msg_text:
            potential_text = clean_msg_text.replace("🎤", "").strip()
            if potential_text:
                text_to_use = potential_text
                is_voice = True

        # 3. Fallback to reply_to_message (Text message case)
        if not text_to_use:
            original_message = bot_message.reply_to_message
            if original_message and original_message.text:
                text_to_use = original_message.text
                is_voice = False
            elif not is_voice:
                # If we didn't find transcription and no reply text -> Error
                await bot_message.edit_text("❌ Content expired or not found.")
                return

    if action == "transcribe_this":
        # Just show the text (transcription)
        safe_text = html.escape(text_to_use)
        final_text = f"🎤 <i>{safe_text}</i>"

        # Next step buttons
        keyboard = [
            [InlineKeyboardButton("🌐 Translate", callback_data="translate_this")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await bot_message.edit_text(
            final_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )

    elif action == "translate_this":
        # Perform translation
        translation = await translator_service.translate_message(
            text_to_use, bot_message.chat_id
        )

        if not translation:
            await bot_message.edit_text("❌ Translation failed.")
            return

        # Format output
        safe_translation = html.escape(translation)

        final_text = safe_translation
        if is_voice:
            # Show transcription AND translation
            safe_transcription = html.escape(text_to_use)
            final_text = f"🎤 <i>{safe_transcription}</i>\n{safe_translation}"

        # Add Speak button for the translated text
        keyboard = [[InlineKeyboardButton("🔊 Speak", callback_data="speak")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await bot_message.edit_text(
                final_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error editing message with translation: {e}")
            await bot_message.edit_text(
                f"{text_to_use}\n\nTranslation: {translation}",
                reply_markup=reply_markup,
            )
