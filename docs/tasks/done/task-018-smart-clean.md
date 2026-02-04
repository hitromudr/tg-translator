# Improvement: Smart Clean Command

**Status**: In Progress
**ID**: task-018

## Description
The current `/clean` command implementation is naive: it iterates backwards a fixed number of times (default 10) and tries to delete messages. If there are user messages in between bot messages, the loop exhausts its iterations on messages it cannot delete, failing to clean up older bot messages that are still relatively recent (e.g., sent 20 minutes ago).

We need a "Smart Clean" strategy that specifically targets deleting the bot's *own* messages (or messages it has permission to delete) up to a requested count, while scanning a larger range of history.

## Goals
1.  **Refactor `clean_command`**:
    -   Implement a two-limit system:
        -   `target_count`: How many messages we *want* to delete (default 10, max 50).
        -   `scan_limit`: How far back we are willing to check (e.g., 200 IDs).
2.  **Logic Update**:
    -   Iterate backwards from the command message ID.
    -   Attempt to delete each message ID.
    -   If successful: Increment `deleted_count`.
    -   If failed (e.g., "Message can't be deleted" because it belongs to another user): Do *not* increment `deleted_count`, just continue scanning.
    -   Stop when `deleted_count == target_count` or `scanned_count == scan_limit`.
3.  **Feedback**:
    -   Provide a clearer summary in the logs (and optionally to the user, though we usually delete the command response too).

## Technical Details
-   **File**: `src/tg_translator/handlers/admin.py`.
-   **Telegram API**: The `delete_message` method raises an exception if the bot cannot delete the message. We must catch specific exceptions (like `BadRequest`) to distinguish between "doesn't exist" and "can't delete".
-   **Safety**: Ensure `scan_limit` isn't too high to avoid hitting rate limits (`FloodWait`). A safe upper bound for scanning is around 200-300 IDs per command invocation.

## Benefits
-   **Effectiveness**: Bot effectively cleans up its own clutter even in active groups with many user messages.
-   **Usability**: Users don't have to run `/clean` multiple times to reach older messages.