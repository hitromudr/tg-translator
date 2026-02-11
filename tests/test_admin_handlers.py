from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update
from telegram.ext import ContextTypes

from tg_translator.handlers.admin import help_command, start_command, voice_command


@pytest.mark.asyncio
async def test_start_command_refreshes_scope():
    """
    Verify that start_command refreshes bot commands for the chat scope.
    """
    # Setup
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.set_my_commands = AsyncMock()

    # Mock DB
    mock_db = MagicMock()
    mock_db.set_mode.return_value = True
    context.bot_data = {"db": mock_db}

    # Execute
    await start_command(update, context)

    # Verify set_my_commands IS called
    context.bot.set_my_commands.assert_called_once()

    # Verify reply sent
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_help_command_refreshes_scope():
    """
    Verify that help_command refreshes bot commands for the chat scope.
    """
    # Setup
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.set_my_commands = AsyncMock()

    # Execute
    await help_command(update, context)

    # Verify set_my_commands IS called
    context.bot.set_my_commands.assert_called_once()

    # Verify reply sent
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_voice_command_no_scope_refresh():
    """
    Verify that voice_command no longer attempts to refresh bot commands.
    """
    # Setup
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.set_my_commands = AsyncMock()

    # Mock dependencies
    mock_db = MagicMock()
    mock_db.get_voice_gender.return_value = "female"

    context.bot_data = {"db": mock_db, "translator_service": MagicMock()}
    context.args = []  # No args triggers the info message

    # Execute
    await voice_command(update, context)

    # Verify set_my_commands is NOT called
    context.bot.set_my_commands.assert_not_called()

    # Verify reply sent
    update.message.reply_text.assert_called_once()
