from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from tg_translator.handlers.translation import handle_message


@pytest.mark.asyncio
async def test_handle_message_interactive_mode_saves_text():
    """
    Test that when in interactive mode, text messages are saved to DB
    so they can be retrieved by the callback handler even if reply context is lost.
    """
    # Setup
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.text = "Hello World"
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.username = "testuser"

    # Mock reply_text to return a message object with an ID
    sent_message = MagicMock(spec=Message)
    sent_message.message_id = 999
    update.message.reply_text = AsyncMock(return_value=sent_message)

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_db = MagicMock()
    # Mode is interactive
    mock_db.get_mode.return_value = "interactive"
    # Languages
    mock_db.get_languages.return_value = ("ru", "en")

    context.bot_data = {"db": mock_db, "translator_service": MagicMock()}

    # Execute
    await handle_message(update, context)

    # Verify
    # 1. Reply was sent
    update.message.reply_text.assert_called_once()

    # 2. Text was saved to DB
    expected_key = "12345:999"
    mock_db.add_transcription.assert_called_with(expected_key, "Hello World")
