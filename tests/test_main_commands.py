from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import (
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)
from telegram.ext import Application

# Import the function to be tested
from tg_translator.main import post_init


@pytest.mark.asyncio
async def test_post_init_sets_commands_correctly():
    """
    Test that post_init registers commands for all required scopes:
    1. Default
    2. Private Chats
    3. Group Chats
    4. Group Chat Administrators (Critical fix)
    """
    # Mock the application and its bot
    app = MagicMock(spec=Application)
    app.bot = MagicMock()
    app.bot.set_my_commands = AsyncMock()

    # Call the function
    await post_init(app)

    # Verify set_my_commands was called 4 times
    assert (
        app.bot.set_my_commands.call_count == 4
    ), "set_my_commands should be called 4 times"

    # Get all calls
    calls = app.bot.set_my_commands.call_args_list

    # 1. Default scope (first call)
    # The first call passes commands list without scope kwarg
    args, kwargs = calls[0]
    assert len(args) == 1  # commands list
    assert "scope" not in kwargs or kwargs["scope"] is None

    # 2. Private chats scope
    _, kwargs = calls[1]
    assert isinstance(
        kwargs["scope"], BotCommandScopeAllPrivateChats
    ), "Second call should be for Private Chats"

    # 3. Group chats scope
    _, kwargs = calls[2]
    assert isinstance(
        kwargs["scope"], BotCommandScopeAllGroupChats
    ), "Third call should be for Group Chats"

    # 4. Group chat administrators scope (The Fix)
    _, kwargs = calls[3]
    assert isinstance(
        kwargs["scope"], BotCommandScopeAllChatAdministrators
    ), "Fourth call should be for Group Chat Administrators"
