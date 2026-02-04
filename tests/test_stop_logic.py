from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update
from telegram.ext import ContextTypes

from tg_translator.handlers.admin import stop_command
from tg_translator.handlers.translation import handle_message


@pytest.mark.asyncio
async def test_stop_command():
    """Test that /stop command sets DB mode to 'off'."""
    # Setup
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = AsyncMock(spec=Message)

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_db = MagicMock()
    mock_db.set_mode.return_value = True
    context.bot_data = {"db": mock_db}

    # Act
    await stop_command(update, context)

    # Assert
    mock_db.set_mode.assert_called_with(12345, "off")
    update.message.reply_text.assert_called_once()
    assert "stopped" in update.message.reply_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_off_mode_ignores_message():
    """Test that handle_message does nothing if mode is 'off'."""
    # Setup
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.text = "Hello world"
    update.message.from_user = MagicMock()

    context = MagicMock()
    mock_db = MagicMock()
    mock_db.get_mode.return_value = "off"  # MODE IS OFF

    mock_service = AsyncMock()
    context.bot_data = {"db": mock_db, "translator_service": mock_service}

    # Act
    await handle_message(update, context)

    # Assert
    # Should check mode
    mock_db.get_mode.assert_called_with(12345)
    # Should NOT call translate
    mock_service.translate_message.assert_not_called()


@pytest.mark.asyncio
async def test_interactive_mode_sends_button():
    """Test that handle_message replies with button in interactive mode."""
    # Setup
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = AsyncMock(spec=Message)
    update.message.text = "Hello world"
    update.message.from_user = MagicMock()

    context = MagicMock()
    mock_db = MagicMock()
    mock_db.get_mode.return_value = "interactive"

    mock_service = AsyncMock()
    context.bot_data = {"db": mock_db, "translator_service": mock_service}

    # Act
    await handle_message(update, context)

    # Assert
    # Should check mode
    mock_db.get_mode.assert_called_with(12345)
    # Should NOT call translate automatically
    mock_service.translate_message.assert_not_called()

    # Should reply with a button
    update.message.reply_text.assert_called_once()
    args, kwargs = update.message.reply_text.call_args
    assert args[0] == "..."
    assert "reply_markup" in kwargs

    # Verify the button callback data
    keyboard = kwargs["reply_markup"].inline_keyboard
    assert keyboard[0][0].callback_data == "translate_this"


@pytest.mark.asyncio
async def test_auto_mode_translates_message():
    """Test that handle_message calls translator if mode is auto."""
    # Setup
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = AsyncMock(spec=Message)
    update.message.text = "Hello world"
    update.message.from_user = MagicMock()

    context = MagicMock()
    mock_db = MagicMock()
    mock_db.get_mode.return_value = "auto"  # MODE IS AUTO

    mock_service = AsyncMock()
    # Return a translation different from source to trigger reply
    mock_service.translate_message.return_value = "Привет мир"

    context.bot_data = {"db": mock_db, "translator_service": mock_service}

    # Act
    await handle_message(update, context)

    # Assert
    mock_db.get_mode.assert_called_with(12345)
    mock_service.translate_message.assert_called_with("Hello world", 12345)
    update.message.reply_text.assert_called_once()
