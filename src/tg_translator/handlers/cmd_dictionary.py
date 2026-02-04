import json
import logging
import shlex

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from tg_translator.inflector import HeuristicInflector

logger = logging.getLogger(__name__)


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

    # Access DB from context
    db = context.bot_data["db"]

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
