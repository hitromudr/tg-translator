# Feature: Stop Command & Manual Translation Mode

**Status**: Backlog
**ID**: task-008

## Description
Currently, the bot operates in an "always-on" mode, translating every text message it sees. This can be disruptive in active chats. Users need a way to pause the bot without kicking it. Additionally, a "Manual" or "Interactive" mode is desired where the bot only translates upon request or provides a "Translate" button instead of automatic text generation.

## Goals
1.  **Database Update**:
    -   Extend the database schema (or `chat_settings`) to store the chat's **Operation Mode**.
    -   Modes:
        -   `AUTO` (Default): Current behavior. Immediate translation.
        -   `MANUAL` (Stopped/Muted): Bot ignores text messages unless explicitly triggered.
        -   `INTERACTIVE` (Future): Bot replies with a "Translate" button instead of text.

2.  **Command Implementation**:
    -   `/stop`: Switches mode to `MANUAL`. Bot stops reacting to text messages.
    -   `/start`: Switches mode to `AUTO` (reactivates the bot).
    -   (Optional) `/mode`: A menu to select between Auto, Manual, and Interactive.

3.  **Handler Logic Update (`handle_message`)**:
    -   Check the current mode of the chat before processing.
    -   If `MANUAL`: Return immediately (ignore).
    -   If `AUTO`: Proceed with translation.

4.  **Interactive Mode Prototype (The "Button" Idea)**:
    -   *Concept*: When in `MANUAL` (or a specific `INTERACTIVE` mode), if the bot detects text that looks like it needs translation, it replies with a generic "Translate ⬇️" button.
    -   *Action*: Clicking the button triggers the translation and edits the bot's message to show the result.
    -   *Note*: This requires a callback handler for the specific message ID.

## Technical Details
-   **Storage**: Need to ensure the SQLite DB persists this state across restarts.
-   **UX**: The `/stop` command should reply with "Bot paused. Use /start to resume."
-   **Scope**: For the first iteration, implementing `/stop` (Mute) and `/start` (Unmute) is the priority. The "Button" logic can be added as a setting within the `MANUAL` mode or a separate mode.

## Benefits
-   Reduces spam in group chats.
-   Gives users control over when they need translation.
-   Prevents the bot from translating irrelevant messages in mixed conversations.