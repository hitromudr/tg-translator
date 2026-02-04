from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update
from telegram.ext import ContextTypes

from tg_translator.handlers.admin import clean_command


@pytest.mark.asyncio
async def test_clean_command_smart_logic():
    """
    Test that clean_command skips un-deletable messages (user messages)
    and continues scanning until target_count is met.
    """
    # Setup
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345

    # Command message
    update.message = AsyncMock(spec=Message)
    update.message.message_id = 100
    update.message.delete = AsyncMock()  # Command itself should be deleted

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["2"]  # Target deletion count: 2 messages
    context.bot.delete_message = AsyncMock()

    # Simulation Logic:
    # ID 99: User message (raise Exception)
    # ID 98: Bot message (Success)
    # ID 97: User message (raise Exception)
    # ID 96: Bot message (Success) -> Should stop here (deleted = 2)
    # ID 95: Bot message -> Should NOT reach here

    async def delete_side_effect(chat_id, message_id):
        if message_id in [99, 97]:
            raise Exception("Message can't be deleted")
        if message_id in [98, 96, 95]:
            return True
        return False

    context.bot.delete_message.side_effect = delete_side_effect

    # Act
    await clean_command(update, context)

    # Assert
    # 1. Verify command message deletion was attempted
    update.message.delete.assert_called_once()

    # 2. Verify attempts on specific IDs
    # Expected calls: 99, 98, 97, 96
    expected_calls = [
        ((12345, 99),),
        ((12345, 98),),
        ((12345, 97),),
        ((12345, 96),),
    ]

    # Check actual calls to delete_message
    # Note: call_args_list items are (args, kwargs) tuples.
    # We called it as delete_message(chat_id=..., message_id=...) usually,
    # but the code uses positional or keyword?
    # Code: await context.bot.delete_message(chat_id=chat_id, message_id=target_id)

    assert context.bot.delete_message.call_count == 4

    # Verify ID 95 was NOT attempted because target reached
    call_args = [
        c.kwargs["message_id"] for c in context.bot.delete_message.call_args_list
    ]
    assert 99 in call_args
    assert 98 in call_args
    assert 97 in call_args
    assert 96 in call_args
    assert 95 not in call_args


@pytest.mark.asyncio
async def test_clean_command_scan_limit():
    """
    Test that clean_command respects scan_limit even if target not reached.
    """
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = AsyncMock(spec=Message)
    update.message.message_id = 1000

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["50"]  # High target
    # Always fail deletion
    context.bot.delete_message = AsyncMock(side_effect=Exception("Fail"))

    # In code scan_limit is hardcoded to 200.
    # To avoid running loop 200 times in test, we assume code works,
    # but checking 200 calls is fine for a unit test.

    # Act
    await clean_command(update, context)

    # Assert
    # Should scan exactly 200 times (from 999 down to 800)
    assert context.bot.delete_message.call_count == 200
