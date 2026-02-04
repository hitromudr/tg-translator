import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    if not update.message or not update.effective_chat:
        return

    # Ensure mode is auto (active)
    db = context.bot_data["db"]
    db.set_mode(update.effective_chat.id, "auto")

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
    """Pause the bot (switch to manual mode)."""
    if not update.message or not update.effective_chat:
        return

    db = context.bot_data["db"]
    if db.set_mode(update.effective_chat.id, "manual"):
        await update.message.reply_text(
            "Bot paused. I will not translate automatically until you type /start."
        )
    else:
        await update.message.reply_text("Failed to pause bot.")


async def clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Clean up bot messages.
    Usage: /clean [count] (default 10)
    Tries to delete previous N messages.
    If bot is not admin, it only deletes its own messages.
    """
    if not update.message or not update.effective_chat:
        return

    # Delete the command message itself first
    try:
        await update.message.delete()
        logger.info(f"Deleted command message {update.message.message_id}")
    except Exception as e:
        logger.warning(f"Failed to delete command message: {e}")

    try:
        count = int(context.args[0]) if context.args else 10
        if count > 50:
            count = 50
    except (ValueError, IndexError):
        count = 10

    logger.info(
        f"Starting cleanup of {count} messages in chat {update.effective_chat.id}"
    )

    message_id = update.message.message_id
    chat_id = update.effective_chat.id

    # Try to delete previous messages blindly
    deleted_count = 0
    failed_count = 0
    for i in range(1, count + 1):
        target_id = message_id - i
        if target_id < 1:
            break
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=target_id)
            deleted_count += 1
            logger.info(f"Deleted message {target_id}")
        except Exception as e:
            failed_count += 1
            # Log reason why deletion failed (e.g. "Message can't be deleted")
            logger.info(f"Failed to delete message {target_id}: {e}")
            continue

    logger.info(
        f"Cleanup finished. Deleted {deleted_count}, Failed {failed_count} messages."
    )
