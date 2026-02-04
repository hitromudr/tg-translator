# Feature: Mute Command & Interactive Translation

**Status**: In Progress
**ID**: task-009

## Description
Refine the bot's operation modes to distinguish between "Stopped" (completely silent) and "Muted" (Interactive).
In "Muted" mode, the bot should not automatically translate messages but instead offer a "Translate" button. This allows users to translate specific messages without spamming the chat with auto-translations for everything.

## Goals
1.  **Refine Modes**:
    -   `auto` (Default): Immediate translation.
    -   `off` (was `manual`): Bot ignores everything.
    -   `interactive`: Bot replies with a button.

2.  **Commands**:
    -   `/mute`: Switches chat to `interactive` mode.
    -   Update `/stop` to switch to `off` mode.
    -   Update `/start` to switch to `auto` mode.

3.  **Interactive Logic**:
    -   In `interactive` mode, `handle_message` should reply with a generic "Translate ⬇️" button (InlineKeyboardMarkup).
    -   Create a callback handler for this button (`callback_data="translate_this"`).

4.  **Callback Handler**:
    -   When clicked, the bot retrieves the original text (via `reply_to_message`).
    -   Performs translation.
    -   Edits the button message to show the translation result (and the usual Speak button).

## Technical Details
-   **Database**: The `mode` column already exists. Valid values will be updated to include `interactive` and `off`.
-   **UX**: The "Translate" button should be unobtrusive.
-   **Fallback**: If the original message is deleted, the button might fail to retrieve text. Handle this gracefully (e.g., "Original message not found").

## Benefits
-   **Reduced Noise**: Users control exactly what gets translated.
-   **Convenience**: Translation is still just one click away, unlike `/stop` where you'd have to use a command to translate.