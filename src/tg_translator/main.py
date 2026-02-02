import logging
import os
import sys

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from tg_translator.translator_service import TranslatorService

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Initialize translator service globally or pass via context (global for simplicity here)
translator_service = TranslatorService()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming text messages.
    Translates the message and replies to the user.
    """
    if not update.message or not update.message.text:
        return

    original_text = update.message.text
    user = update.message.from_user
    username = user.username if user else "Unknown"

    logger.info(f"Received message from {username}: {original_text[:50]}...")

    translation = await translator_service.translate_message(original_text)

    if translation and translation != original_text:
        # We reply to the original message with the translation
        await update.message.reply_text(translation)
        logger.info(f"Sent translation: {translation[:50]}...")
    else:
        logger.debug("No translation performed or translation identical to source.")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    if not update.message:
        return
    await update.message.reply_text(
        "Привет! Я бот-переводчик. Я автоматически перевожу сообщения в этом чате.\n"
        "Hi! I am a translator bot. I automatically translate messages in this chat."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    if not update.message:
        return
    await update.message.reply_text(
        "Просто пишите сообщения, и я буду их переводить.\n"
        "Just type messages and I will translate them."
    )


async def post_init(application: Application) -> None:
    """Set up the bot's commands."""
    commands = [
        BotCommand("start", "Start bot / Запуск"),
        BotCommand("help", "Help / Справка"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set successfully.")


def main() -> None:
    """Start the bot."""
    # Load environment variables
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.critical("TELEGRAM_BOT_TOKEN environment variable is not set. Exiting.")
        sys.exit(1)

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(token).post_init(post_init).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - translate the message on Telegram
    # Filter for text messages that are not commands
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
    finally:
        # Ideally we would cleanly shutdown the translator service here if needed,
        # but for this simple script, process termination handles it.
        translator_service.shutdown()
