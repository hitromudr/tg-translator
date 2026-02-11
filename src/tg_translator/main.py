import logging
import os
import socket
import sys

from dotenv import load_dotenv
from telegram import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from tg_translator.commands import BOT_COMMANDS
from tg_translator.db import Database
from tg_translator.handlers.admin import (
    clean_command,
    help_command,
    mute_command,
    start_command,
    status_command,
    stop_command,
    voice_command,
)
from tg_translator.handlers.callback_translate import translate_callback
from tg_translator.handlers.callback_tts import tts_callback
from tg_translator.handlers.cmd_dictionary import dict_command
from tg_translator.handlers.cmd_settings import lang_command
from tg_translator.handlers.translation import handle_message, handle_voice
from tg_translator.translator_service import TranslatorService

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def systemd_notify(message: str) -> None:
    """Notify systemd watchdog."""
    notify_socket = os.getenv("NOTIFY_SOCKET")
    if not notify_socket:
        return

    if notify_socket.startswith("@"):
        notify_socket = "\0" + notify_socket[1:]

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(notify_socket)
            sock.sendall(message.encode())
    except Exception as e:
        logger.warning(f"Failed to notify systemd: {e}")


async def heartbeat_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send heartbeat to systemd watchdog."""
    systemd_notify("WATCHDOG=1")


async def post_init(application: Application) -> None:
    """Set up the bot's commands."""
    # Set commands for default scope
    await application.bot.set_my_commands(BOT_COMMANDS)

    # Set commands for private chats
    await application.bot.set_my_commands(
        BOT_COMMANDS, scope=BotCommandScopeAllPrivateChats()
    )

    # Set commands for group chats
    await application.bot.set_my_commands(
        BOT_COMMANDS, scope=BotCommandScopeAllGroupChats()
    )

    # Set commands for group chat administrators
    await application.bot.set_my_commands(
        BOT_COMMANDS, scope=BotCommandScopeAllChatAdministrators()
    )

    # Set up watchdog heartbeat (every 30s)
    if os.getenv("NOTIFY_SOCKET") and application.job_queue:
        application.job_queue.run_repeating(heartbeat_job, interval=30, first=10)
        logger.info("Systemd watchdog heartbeat enabled.")

    logger.info("Bot commands set successfully for all scopes.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)


def main() -> None:
    """Start the bot."""
    # Load environment variables
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.critical("TELEGRAM_BOT_TOKEN environment variable is not set. Exiting.")
        sys.exit(1)

    # Initialize services
    db = Database()
    translator_service = TranslatorService(db=db)

    # Create the Application and pass it your bot's token.
    # Set higher timeouts and pool size to avoid connection issues with proxy
    request = HTTPXRequest(
        connect_timeout=10.0,
        read_timeout=15.0,
        write_timeout=15.0,
        pool_timeout=10.0,
        connection_pool_size=50,  # Increased from 20 to 50
    )
    application = (
        Application.builder().token(token).request(request).post_init(post_init).build()
    )

    # Add error handler
    application.add_error_handler(error_handler)

    # Inject dependencies into bot_data so handlers can access them
    application.bot_data["db"] = db
    application.bot_data["translator_service"] = translator_service

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("dict", dict_command))
    application.add_handler(CommandHandler("lang", lang_command))
    application.add_handler(CommandHandler("voice", voice_command))
    application.add_handler(CommandHandler("clean", clean_command))
    application.add_handler(CommandHandler("status", status_command))

    application.add_handler(
        CallbackQueryHandler(
            translate_callback, pattern="^(transcribe|translate)_this$"
        )
    )
    application.add_handler(CallbackQueryHandler(tts_callback))

    # on non command i.e message - translate the message on Telegram
    # Filter for text messages that are not commands
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Filter for voice messages
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
