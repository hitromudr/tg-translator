import html
import logging
import os
import sys

from dotenv import load_dotenv
from telegram import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from tg_translator.db import Database
from tg_translator.inflector import HeuristicInflector
from tg_translator.translator_service import TranslatorService

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Initialize database
db = Database()

# Initialize translator service globally or pass via context (global for simplicity here)
translator_service = TranslatorService(db=db)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming text messages.
    Translates the message and replies to the user.
    """
    if not update.message or not update.message.text or not update.effective_chat:
        return

    original_text = update.message.text
    user = update.message.from_user
    username = user.username if user else "Unknown"

    logger.info(f"Received message from {username}: {original_text[:50]}...")

    translation = await translator_service.translate_message(
        original_text, update.effective_chat.id
    )

    if translation and translation != original_text:
        # We reply to the original message with the translation
        safe_translation = html.escape(translation)
        spoiler_text = f'<span class="tg-spoiler">{safe_translation}</span>'
        await update.message.reply_text(spoiler_text, parse_mode=ParseMode.HTML)
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

    user = update.message.from_user
    username = user.username if user else "Unknown"
    logger.info(f"Received voice message from {username}")

    try:
        voice_file = await update.message.voice.get_file()

        # Create temp directory if not exists
        os.makedirs("tmp", exist_ok=True)

        file_path = f"tmp/voice_{update.message.voice.file_unique_id}.ogg"
        await voice_file.download_to_drive(file_path)

        transcription = await translator_service.transcribe_audio(file_path)

        if transcription:
            logger.info(f"Transcribed text: {transcription[:50]}...")
            translation = await translator_service.translate_message(
                transcription, update.effective_chat.id
            )

            response_parts = []
            response_parts.append(f"🎤 <i>{html.escape(transcription)}</i>")

            if translation and translation.lower() != transcription.lower():
                safe_translation = html.escape(translation)
                response_parts.append(
                    f'<span class="tg-spoiler">{safe_translation}</span>'
                )

            await update.message.reply_text(
                "\n".join(response_parts), parse_mode=ParseMode.HTML
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
        "🤖 <b>Справка:</b>\n\n"
        "💬 <b>Перевод:</b> Просто пишите текст или отправляйте голосовые — я переведу их автоматически.\n\n"
        "📖 <b>Словарь (если я ошибаюсь в именах):</b>\n"
        "• <code>/dict add Ян Ian</code> — научить меня переводить 'Ян' как 'Ian' (падежи добавлю сам!).\n"
        "• <code>/dict list</code> — посмотреть список замен.\n"
        "• <code>/dict remove Ян</code> — забыть замену.\n\n"
        "🇬🇧 <b>English:</b>\n"
        "Just type messages. Use <code>/dict add Source Target</code> to fix specific translations.",
        parse_mode=ParseMode.HTML,
    )


async def dict_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle dictionary commands:
    /dict add <source> <target>
    /dict remove <source>
    /dict list
    """
    if not update.message or not update.effective_chat:
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n/dict add <word> <translation>\n/dict remove <word>\n/dict list"
        )
        return

    subcommand = context.args[0].lower()
    chat_id = update.effective_chat.id

    if subcommand == "add":
        if len(context.args) < 3:
            await update.message.reply_text("Usage: /dict add <word> <translation>")
            return
        source = context.args[1]
        # target might contain spaces, so join the rest
        target = " ".join(context.args[2:])

        # Use heuristic inflector to generate variations (e.g. Russian cases)
        variations = HeuristicInflector.get_variations(source)
        # Ensure we always try to add at least the exact word provided
        if not variations:
            variations = {source}

        count = 0
        for variant in variations:
            if db.add_term(chat_id, variant, target):
                count += 1

        if count > 0:
            msg = f"Added: '{source}' -> '{target}'"
            if count > 1:
                msg += f"\nAnd {count - 1} automatic variations (cases/forms)."
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("Failed to add term.")

    elif subcommand == "remove":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /dict remove <word>")
            return
        source = context.args[1]
        if db.remove_term(chat_id, source):
            await update.message.reply_text(f"Removed: '{source}'")
        else:
            await update.message.reply_text(f"Term '{source}' not found.")

    elif subcommand == "list":
        terms = db.get_terms(chat_id)
        if not terms:
            await update.message.reply_text("Dictionary is empty.")
        else:
            msg = "Custom Dictionary:\n"
            for source, target in terms:
                msg += f"- {source} -> {target}\n"
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text("Unknown subcommand. Use add, remove, or list.")


async def post_init(application: Application) -> None:
    """Set up the bot's commands."""
    commands = [
        BotCommand("start", "Start bot / Запуск"),
        BotCommand("help", "Help / Справка"),
        BotCommand("dict", "Manage dictionary / Словарь"),
    ]
    # Set commands for default scope
    await application.bot.set_my_commands(commands)

    # Set commands for private chats
    await application.bot.set_my_commands(
        commands, scope=BotCommandScopeAllPrivateChats()
    )

    # Set commands for group chats
    await application.bot.set_my_commands(
        commands, scope=BotCommandScopeAllGroupChats()
    )

    logger.info("Bot commands set successfully for all scopes.")


def main() -> None:
    """Start the bot."""
    # Load environment variables
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.critical("TELEGRAM_BOT_TOKEN environment variable is not set. Exiting.")
        sys.exit(1)

    # Create the Application and pass it your bot's token.
    # Set higher timeouts to avoid connection issues
    request = HTTPXRequest(connect_timeout=20.0, read_timeout=20.0, write_timeout=20.0)
    application = (
        Application.builder().token(token).request(request).post_init(post_init).build()
    )

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("dict", dict_command))

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
