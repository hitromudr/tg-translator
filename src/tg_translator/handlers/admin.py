import logging
import os

from telegram import BotCommandScopeChat, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from tg_translator.commands import BOT_COMMANDS

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    if not update.message or not update.effective_chat:
        return

    # Ensure mode is auto (active)
    db = context.bot_data["db"]
    db.set_mode(update.effective_chat.id, "auto")

    # Force update commands for this specific chat
    try:
        await context.bot.set_my_commands(
            BOT_COMMANDS, scope=BotCommandScopeChat(update.effective_chat.id)
        )
    except Exception as e:
        logger.error(
            f"Failed to refresh commands for chat {update.effective_chat.id}: {e}"
        )

    await update.message.reply_text(
        "Привет! Я бот-переводчик. Я автоматически перевожу сообщения в этом чате.\n"
        "Hi! I am a translator bot. I automatically translate messages in this chat."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    if not update.message or not update.effective_chat:
        return

    # Force update commands for this specific chat
    try:
        await context.bot.set_my_commands(
            BOT_COMMANDS, scope=BotCommandScopeChat(update.effective_chat.id)
        )
    except Exception as e:
        logger.error(
            f"Failed to refresh commands for chat {update.effective_chat.id}: {e}"
        )

    await update.message.reply_text(
        "🤖 <b>Справка / Help</b>\n\n"
        "⚙️ <b>Режимы работы / Modes:</b>\n"
        "• /start — <b>Авто</b> (переводит всё подряд / translates everything).\n"
        "• /mute — <b>Интерактив</b> (кнопка перевода по запросу / translate on click).\n"
        "• /stop — <b>Выкл</b> (бот спит / bot disabled).\n\n"
        "🗣 <b>Голос / Voice:</b>\n"
        "• <code>/voice male</code> | <code>female</code> — Пол голоса / Voice gender.\n"
        "• <code>/voice test en en_45</code> — Тест спикера / Test specific speaker.\n"
        "• <code>/voice set en male en_45</code> — Назначить спикера / Set preset.\n\n"
        "📖 <b>Словарь / Dictionary:</b>\n"
        "• <code>/dict add Ян Ian</code> — Добавить замену / Add term.\n"
        "• <code>/dict remove Ян</code> — Удалить / Remove.\n"
        "• <code>/dict list</code> — Список / List.\n"
        "• <code>/dict export</code> | <code>import</code> — Бэкап / Backup.\n\n"
        "🌍 <b>Настройки / Settings:</b>\n"
        "• <code>/lang set ru en</code> — Пара языков / Language pair.\n"
        "• <code>/clean</code> — Очистка сообщений бота / Clean bot messages.",
        parse_mode=ParseMode.HTML,
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop the bot (switch to 'off' mode)."""
    if not update.message or not update.effective_chat:
        return

    db = context.bot_data["db"]
    if db.set_mode(update.effective_chat.id, "off"):
        await update.message.reply_text(
            "Bot stopped. I will not translate anything until you type /start or /mute."
        )
    else:
        await update.message.reply_text("Failed to stop bot.")


async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch to interactive mode (translation by button)."""
    if not update.message or not update.effective_chat:
        return

    db = context.bot_data["db"]
    if db.set_mode(update.effective_chat.id, "interactive"):
        await update.message.reply_text(
            "Bot muted. I will reply with a 'Translate' button instead of auto-translating."
        )
    else:
        await update.message.reply_text("Failed to mute bot.")


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manage voice settings.
    Usage:
    /voice [male|female] - Quick toggle
    /voice test <lang> <speaker> - Preview
    /voice set <lang> <gender> <speaker> - Set preset
    /voice reset - Clear presets
    """
    if not update.message or not update.effective_chat:
        return

    args = context.args
    db = context.bot_data["db"]
    service = context.bot_data["translator_service"]
    chat_id = update.effective_chat.id

    # Force update commands for this specific chat
    try:
        await context.bot.set_my_commands(
            BOT_COMMANDS, scope=BotCommandScopeChat(update.effective_chat.id)
        )
    except Exception as e:
        logger.error(
            f"Failed to refresh commands for chat {update.effective_chat.id}: {e}"
        )

    if not args:
        current_gender = db.get_voice_gender(chat_id)
        msg = f"Current global gender: <b>{current_gender}</b>\n\n"
        msg += (
            "<b>Usage:</b>\n"
            "• <code>/voice male</code> or <code>female</code> - Switch global preference.\n"
            "• <code>/voice test en en_45</code> - Test a speaker.\n"
            "• <code>/voice set en male en_45</code> - Assign speaker to lang/gender.\n"
            "• <code>/voice reset</code> - Clear all custom presets."
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    subcommand = args[0].lower()

    # Legacy: /voice male | female
    if subcommand in ["male", "female"]:
        if db.set_voice_gender(chat_id, subcommand):
            await update.message.reply_text(f"Global voice gender set to: {subcommand}")
        else:
            await update.message.reply_text("Failed to set voice gender.")
        return

    if subcommand == "test":
        if len(args) < 3:
            await update.message.reply_text(
                "Usage: /voice test <lang> <speaker>\nExample: /voice test en en_45"
            )
            return

        lang = args[1].lower()
        speaker = args[2]

        text_map = {
            "ru": "Это тест выбранного голоса.",
            "en": "This is a test of the selected voice.",
            "uk": "Це тест вибраного голосу.",
            "ua": "Це тест вибраного голосу.",
        }
        test_text = text_map.get(lang, "This is a test of the selected voice.")

        try:
            path = await service.generate_audio(
                test_text, lang, speaker_override=speaker
            )
            if path:
                await update.message.reply_voice(open(path, "rb"))
                os.remove(path)
            else:
                await update.message.reply_text(
                    f"Failed to generate audio for {lang}/{speaker}."
                )
        except Exception as e:
            logger.error(f"Voice test error: {e}")
            await update.message.reply_text("Error generating audio.")

    elif subcommand == "set":
        # /voice set en male en_45
        if len(args) < 4:
            await update.message.reply_text(
                "Usage: /voice set <lang> <gender> <speaker>\nExample: /voice set en male en_92"
            )
            return

        lang = args[1].lower()
        gender = args[2].lower()
        speaker = args[3]

        if gender not in ["male", "female"]:
            await update.message.reply_text("Gender must be 'male' or 'female'.")
            return

        if db.set_voice_preset(chat_id, lang, gender, speaker):
            await update.message.reply_text(
                f"Saved preset: {lang.upper()} ({gender}) -> {speaker}"
            )
        else:
            await update.message.reply_text("Failed to save preset.")

    elif subcommand == "reset":
        if db.delete_voice_presets(chat_id):
            await update.message.reply_text("All custom voice presets cleared.")
        else:
            await update.message.reply_text("Failed to clear presets.")

    else:
        await update.message.reply_text(
            "Unknown command. Use: male, female, test, set, reset."
        )


async def clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Clean up bot messages.
    Usage: /clean [target_count] (default 10, max 50)
    Smart scanning: Scans up to 200 previous messages to find bot messages.
    """
    if not update.message or not update.effective_chat:
        return

    # Delete the command message itself first
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete command message: {e}")

    try:
        target_count = int(context.args[0]) if context.args else 10
        if target_count > 50:
            target_count = 50
    except (ValueError, IndexError):
        target_count = 10

    # Scan limit: How far back to check.
    # This prevents infinite loops if there are no bot messages.
    scan_limit = 200

    logger.info(
        f"Starting smart cleanup. Target: {target_count}, Scan limit: {scan_limit} in chat {update.effective_chat.id}"
    )

    current_id = update.message.message_id
    chat_id = update.effective_chat.id

    deleted_count = 0
    scanned_count = 0

    # Iterate backwards
    for i in range(1, scan_limit + 1):
        # Stop if we reached our target deletion count
        if deleted_count >= target_count:
            break

        scanned_count += 1
        target_id = current_id - i
        if target_id < 1:
            break

        try:
            # delete_message returns True on success
            await context.bot.delete_message(chat_id=chat_id, message_id=target_id)
            deleted_count += 1
            # logger.debug(f"Deleted message {target_id}")
        except Exception:
            # If failed (e.g. "Message can't be deleted" -> not ours, or "Message not found"),
            # just continue scanning. We don't count this as a "deletion attempt" against our target_count.
            continue

    logger.info(
        f"Cleanup finished. Deleted {deleted_count} messages after scanning {scanned_count} IDs."
    )
