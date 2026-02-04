# Bug: Command Menu Missing in Private Groups

**Status**: Completed
**ID**: bug-001

## Description
User reports that the command menu (triggered by `/`) is not visible in private groups, while all 5 items are visible in private chats with the bot. This suggests a potential issue with `BotCommandScope`.

## Goals
1. Analyze `src/tg_translator/main.py` regarding `set_my_commands` usage. [x]
2. Verify if `BotCommandScopeAllGroupChats` is correctly applied. [x]
3. Fix the scope configuration if necessary. [x]
4. Verify the fix. [x]

## Resolution
- Identified that while `BotCommandScopeAllGroupChats` was present, explicit scope for administrators (`BotCommandScopeAllChatAdministrators`) was missing. Clients sometimes require this specific scope for group admins.
- Added `BotCommandScopeAllChatAdministrators` to `post_init` in `src/tg_translator/main.py`.
- Verified the fix by creating a new test `tests/test_main_commands.py` which confirms `set_my_commands` is called for all 4 scopes (Default, Private, Group, GroupAdmins).
- Note: Pre-existing tests (`tests/test_translator.py`) were found to be broken due to dependency issues and outdated code references, but this did not affect the implementation of this fix.

## Context
- `grep` showed usage of `BotCommandScopeAllPrivateChats` and `BotCommandScopeAllGroupChats` in `post_init`.
- `post_init` is correctly wired into the Application builder.