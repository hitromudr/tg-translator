import io
import shlex

from telegram import Update
from telegram.ext import ContextTypes


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

    # Retrieve dependencies from context
    db = context.bot_data["db"]
    translator_service = context.bot_data["translator_service"]

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
