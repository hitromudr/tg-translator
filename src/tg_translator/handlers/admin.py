import logging

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
    if not update.message:
        return
    await update.message.reply_text(
        "🤖 <b>Справка:</b>\n\n"
        "💬 <b>Перевод:</b> Просто пишите текст или отправляйте голосовые — я переведу их автоматически.\n\n"
        "📖 <b>Словарь (если я ошибаюсь в именах):</b>\n"
        "• <code>/dict add Ян Ian</code> — научить меня переводить 'Ян' как 'Ian' (падежи добавлю сам!).\n"
        '• <code>/dict add "фраза с пробелами" Перевод</code> — используйте кавычки для фраз.\n'
        "• <code>/dict list</code> — посмотреть список замен.\n"
        "• <code>/dict remove Ян</code> — забыть замену.\n"
        "• <code>/dict export</code> — получить код для переноса словаря.\n"
        "• <code>/dict import CODE</code> — загрузить словарь по коду.\n\n"
        "🌍 <b>Языки / Languages:</b>\n"
        "• <code>/lang set ru de</code> — переключить пару на Русский-Немецкий.\n"
        "• <code>/lang reset</code> — сброс (ru-en).\n\n"
        "🇬🇧 <b>English:</b>\n"
        "Just type messages. Use <code>/dict</code> to fix translations, <code>/lang</code> to switch languages.",
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
    """Set voice gender: /voice male or /voice female."""
    if not update.message or not update.effective_chat:
        return

    args = context.args
    db = context.bot_data["db"]

    if not args:
        # Show status
        current = db.get_voice_gender(update.effective_chat.id)
        await update.message.reply_text(
            f"Current voice: {current}\nUsage: /voice male | female"
        )
        return

    gender = args[0].lower()
    if gender not in ["male", "female"]:
        await update.message.reply_text("Invalid gender. Use: male or female")
        return

    if db.set_voice_gender(update.effective_chat.id, gender):
        await update.message.reply_text(f"Voice set to: {gender}")
    else:
        await update.message.reply_text("Failed to set voice.")


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
