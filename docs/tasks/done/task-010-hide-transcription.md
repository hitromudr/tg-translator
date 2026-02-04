# Feature: Hide Voice Transcription (Lazy Display)

**Status**: In Progress
**ID**: task-010

## Description
In `interactive` (mute) mode, the bot currently displays the transcribed text of a voice message immediately above the "Translate" button. This consumes chat space. The goal is to hide this transcription and only reveal it (along with the translation) when the user clicks the button. Since the original voice message doesn't contain the text, the bot must temporarily store the transcription until the button is clicked.

## Goals
1.  **Database Update**:
    -   Create a new table `transcriptions` to temporarily store the transcribed text.
    -   Schema: `key` (TEXT PK), `text` (TEXT), `created_at` (TIMESTAMP).
    -   The `key` will be a composite of `chat_id:message_id` (the bot's reply message ID).

2.  **Update `handle_voice` (Interactive Mode)**:
    -   Perform STT (Speech-to-Text) transcription.
    -   Send a minimal reply: "🎤 Voice message" + [Translate ⬇️] button.
    -   Capture the sent message's ID.
    -   Store the transcription in the DB linked to that message ID.

3.  **Update `callback_translate`**:
    -   Logic check: If the message text is the placeholder (e.g., "🎤 Voice message"), look up the transcription in the DB.
    -   Perform translation on the retrieved text.
    -   Edit the message to show: `🎤 Transcription` + `Translation`.
    -   Delete the DB entry (one-time use).

## Technical Details
-   **Storage**: Use the existing SQLite DB. Add a simple key-value store table for transcriptions.
-   **Concurrency**: Ensure the storage happens immediately after sending the reply so the user can't click the button before the data is saved (unlikely given network latency, but `await` order matters).
-   **Cleanup**: Update the existing cleanup logic (used for exports) to also purge old transcriptions (e.g., > 24h) to prevent DB bloat if buttons are never clicked.

## Benefits
-   **Minimalism**: Reduces visual noise in the chat.
-   **Consistency**: Works similarly to text messages where the bot's intervention is minimal until requested.