import html
import io
import json
import logging
import os
import shlex
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
    if user:
        username = user.username or user.first_name
    else:
        username = "Unknown"

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
    if user:
        username = user.username or user.first_name
    else:
        username = "Unknown"
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


async def dict_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle dictionary commands:
    /dict add <source> <target>
    /dict remove <source>
    /dict list
    /dict export
    /dict import <code >
    """
    if not update.message or not update.effective_chat or not update.message.text:
        return

    # Parse arguments using shlex to support quotes for phrases
    try:
        # text includes the command itself, e.g. "/dict add ..."
        args = shlex.split(update.message.text)
    except ValueError as e:
        await update.message.reply_text(f"Error parsing arguments: {e}")
        return

    # args[0] is the command (e.g. /dict), args[1] is subcommand
    if len(args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "/dict add <word> <translation>\n"
            "/dict remove <word>\n"
            "/dict list\n"
            "/dict export\n"
            "/dict import <code>\n\n"
            'Use quotes for phrases: /dict add "phrase one" translation'
        )
        return

    subcommand = args[1].lower()
    chat_id = update.effective_chat.id

    # Get current language pair to use for dictionary operations
    l1, l2 = db.get_languages(chat_id)
    langs = sorted([l1, l2])
    lang_pair = f"{langs[0]}-{langs[1]}"

    if subcommand == "add":
        if len(args) < 4:
            await update.message.reply_text(
                'Usage: /dict add <word> <translation>\nUse quotes for phrases: /dict add "source phrase" target'
            )
            return
        source = args[2]
        # Target is everything else. Since shlex stripped quotes from individual args,
        # joining them with space is a reasonable approximation for the target.
        target = " ".join(args[3:])

        # Use heuristic inflector to generate variations (e.g. Russian cases)
        variations = HeuristicInflector.get_variations(source)
        # Ensure we always try to add at least the exact word provided
        if not variations:
            variations = {source}

        count = 0
        for variant in variations:
            if db.add_term(chat_id, variant, target, lang_pair):
                count += 1

        if count > 0:
            msg = f"Added ({l1}-{l2}): '{source}' -> '{target}'"
            if count > 1:
                msg += f"\nAnd {count - 1} automatic variations (cases/forms)."
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("Failed to add term.")

    elif subcommand == "remove":
        if len(args) < 3:
            await update.message.reply_text(
                'Usage: /dict remove <word>\nUse quotes for phrases: /dict remove "source phrase"'
            )
            return
        source = args[2]
        if db.remove_term(chat_id, source, lang_pair):
            await update.message.reply_text(f"Removed ({l1}-{l2}): '{source}'")
        else:
            await update.message.reply_text(f"Term '{source}' not found.")

    elif subcommand == "list":
        terms = db.get_terms(chat_id, lang_pair)
        if not terms:
            await update.message.reply_text(f"Dictionary is empty for {l1}-{l2}.")
        else:
            msg = f"Custom Dictionary ({l1}-{l2}):\n"
            for source, target in terms:
                msg += f"- {source} -> {target}\n"
            await update.message.reply_text(msg)

    elif subcommand == "export":
        terms = db.get_terms(chat_id, lang_pair)
        if not terms:
            await update.message.reply_text("Dictionary is empty, nothing to export.")
            return

        data = json.dumps(terms)
        code = db.create_export(data)
        if code:
            await update.message.reply_text(
                f"Dictionary exported! Code: <code>{code}</code>\n"
                "Valid for 24 hours. Use /dict import to load in another chat.",
                parse_mode=ParseMode.HTML,
            )
        else:
            await update.message.reply_text("Failed to create export.")

    elif subcommand == "import":
        if len(args) < 3:
            await update.message.reply_text("Usage: /dict import <CODE>")
            return
        code = args[2]
        data_str = db.get_export(code)
        if not data_str:
            await update.message.reply_text("Invalid or expired code.")
            return

        try:
            terms = json.loads(data_str)
            count = 0
            for src, tgt in terms:
                if db.add_term(chat_id, src, tgt, lang_pair):
                    count += 1
            await update.message.reply_text(
                f"Successfully imported {count} terms to {l1}-{l2} dictionary."
            )
        except Exception as e:
            logger.error(f"Import error: {e}")
            await update.message.reply_text("Error importing dictionary data.")

    else:
        await update.message.reply_text(
            "Unknown subcommand. Use add, remove, list, export, or import."
        )


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle language configuration:
    /lang set <l1> <l2>
    /lang reset
    /lang status
    """
    if not update.message or not update.effective_chat or not update.message.text:
        return

    try:
        args = shlex.split(update.message.text)
    except ValueError:
        args = update.message.text.split()

    if len(args) < 2:
        await update.message.reply_text(
            "Usage:\n/lang set <lang1> <lang2>\n/lang reset\n/lang status\n/lang list"
        )
        return

    subcommand = args[1].lower()
    chat_id = update.effective_chat.id

    if subcommand == "set":
        if len(args) < 4:
            await update.message.reply_text(
                "Usage: /lang set <primary> <secondary>\nExample: /lang set ru es"
            )
            return
        l1 = translator_service.normalize_language_code(args[2])
        if not l1:
            await update.message.reply_text(
                f"Error: Language '{args[2]}' is not supported.\nUse /lang list to see available codes."
            )
            return

        l2 = translator_service.normalize_language_code(args[3])
        if not l2:
            await update.message.reply_text(
                f"Error: Language '{args[3]}' is not supported.\nUse /lang list to see available codes."
            )
            return

        if db.set_languages(chat_id, l1, l2):
            await update.message.reply_text(f"Languages set: {l1} <-> {l2}")
        else:
            await update.message.reply_text("Failed to set languages.")

    elif subcommand == "reset":
        if db.set_languages(chat_id, "ru", "en"):
            await update.message.reply_text("Languages reset to: ru <-> en")
        else:
            await update.message.reply_text("Failed to reset languages.")

    elif subcommand == "status":
        l1, l2 = db.get_languages(chat_id)
        await update.message.reply_text(f"Current languages: {l1} <-> {l2}")

    elif subcommand == "list":
        supported = translator_service.get_supported_languages()
        # Format: Name: code
        lines = [f"{name.title()}: {code}" for name, code in supported.items()]
        text = "Supported Languages:\n\n" + "\n".join(sorted(lines))

        file = io.BytesIO(text.encode("utf-8"))
        file.name = "languages.txt"

        await update.message.reply_document(
            document=file, caption="List of supported languages and their codes."
        )

    else:
        await update.message.reply_text("Unknown subcommand.")


async def post_init(application: Application) -> None:
    """Set up the bot's commands."""
    commands = [
        BotCommand("start", "Start bot / Запуск"),
        BotCommand("help", "Help / Справка"),
        BotCommand("dict", "Manage dictionary / Словарь"),
        BotCommand("lang", "Settings / Языки"),
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
    application.add_handler(CommandHandler("lang", lang_command))

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
