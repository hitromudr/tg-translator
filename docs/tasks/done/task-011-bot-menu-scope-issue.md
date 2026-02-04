# Task-011: Fix Bot Menu Scope in Private Groups

## Status
- **Priority**: High
- **Status**: Done

## Context
Despite previous fixes (Bug-001), there are reports of issues with the Bot Command Menu visibility in Private Groups. Specifically, the usage of `BotCommandScopeChat` inside command handlers (`start`, `help`, `voice`) has been flagged as potentially problematic.
The current implementation attempts to force-refresh the menu for the specific chat upon certain commands, but this might be redundant, hitting API limits, or conflicting with the `BotCommandScopeAllGroupChats` / `BotCommandScopeAllChatAdministrators` scopes set during `post_init`.

## Goals
1.  **Analyze `BotCommandScopeChat` Usage**: Investigate if calling `set_my_commands` with `BotCommandScopeChat` inside individual command handlers is necessary or harmful.
2.  **Verify Private Group Behavior**: Confirm whether the menu persists correctly for all members in a Private Group (supergroup) without these per-command calls.
3.  **Optimize Menu Logic**: Remove redundant calls if the global scopes (`AllGroupChats`, `AllChatAdministrators`) defined in `post_init` are sufficient.
4.  **Fix Scope Conflicts**: Ensure that specific chat settings do not accidentally break the menu for that chat or others.

## Implementation Plan
1.  Review `src/tg_translator/handlers/admin.py` where `set_my_commands` is called.
2.  Review `src/tg_translator/main.py` `post_init` logic.
3.  Test behavior:
    - If `BotCommandScopeAllGroupChats` is set, does a specific private group need an explicit `BotCommandScopeChat` override? Usually not, unless the commands *differ* for that chat.
    - Since the commands (`BOT_COMMANDS`) are identical for all scopes currently, the per-chat override seems redundant and wasteful (API calls).
4.  Refactor:
    - Likely remove the `set_my_commands` calls from `admin.py` handlers.
    - Rely on `post_init` to set scopes globally.
    - If a "Refresh" is truly needed, ensure it's done correctly.

## Acceptance Criteria
- [x] Redundant `set_my_commands` calls removed from command handlers (`start`, `help`, `voice`).
- [x] Bot menu successfully appears in Private Groups (via `post_init` scope).
- [x] Bot menu successfully appears for Admins.
- [x] No regression in command availability.