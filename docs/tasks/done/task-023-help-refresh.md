# Fix: Outdated Help & Command Menu Refresh

**Status**: In Progress
**ID**: task-023

## Description
1.  **Help Text**: The `/help` message is severely outdated. It doesn't mention new features like `/stop` (Off), `/mute` (Interactive), `/voice` (Gender/Presets), or the advanced dictionary logic.
2.  **Command Menu**: The command menu (`/` menu) often fails to update on client devices due to aggressive caching by Telegram clients. Relying solely on `/start` to refresh it is insufficient.

## Goals
1.  **Rewrite Help**:
    -   Update `help_command` in `src/tg_translator/handlers/admin.py`.
    -   Include sections for: Translation Modes (`/start`, `/stop`, `/mute`), Voice Control (`/voice`), Dictionary, and Settings.
2.  **Force Refresh**:
    -   Add a call to `set_my_commands(scope=Chat)` inside `help_command` and potentially `voice_command`. This ensures that whenever a user interacts with bot settings, their menu gets refreshed.

## Technical Details
-   **File**: `src/tg_translator/handlers/admin.py`
-   **Content**:
    -   **Modes**: Auto (Start), Interactive (Mute), Off (Stop).
    -   **Voice**: Gender toggle, Test, Set presets.
    -   **Lang**: Set pair.
    -   **Dict**: Add/Remove.

## Benefits
-   **Usability**: Users know about all features.
-   **Stability**: Command menu stays in sync.