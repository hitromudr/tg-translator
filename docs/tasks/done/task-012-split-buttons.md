# Feature: Split Voice Buttons & Fix Bubble Size

**Status**: In Progress
**ID**: task-012

## Description
The previous attempt to minimize the bot's reply bubble using emojis with zero-width spaces did not fully solve the "large sticker" rendering issue on some Telegram clients. Additionally, users requested more granular control over voice messages: the ability to just see the text (transcription) without translating it immediately.

## Goals
1.  **Fix Bubble Size**:
    -   Replace placeholder emojis (`🎤`, `📝`) with `...` (three dots). This guarantees a minimal text bubble on all clients.

2.  **Voice Message UI**:
    -   Instead of a single "Translate" button, offer two buttons in a row:
        -   `[ 📝 Text ]`: Shows only the transcription.
        -   `[ 🌐 Translate ]`: Shows transcription + translation.

3.  **Text Message UI**:
    -   Keep the single `[ 🌐 Translate ]` button (since transcription isn't needed).

4.  **Callback Logic**:
    -   Implement `transcribe_this` action: fetches text from DB and displays it.
    -   Update `translate_this` action: fetches text, translates, and displays result.

## Technical Details
-   **Handlers**: Update `handlers/translation.py` to use `...` and the new `InlineKeyboardMarkup` layout.
-   **Callbacks**: Update `handlers/callback_translate.py` to handle the `transcribe_this` case.
-   **Routing**: Update `main.py` `CallbackQueryHandler` regex to include `transcribe_this`.

## Benefits
-   **UX**: Users can choose to just read a voice message in its original language.
-   **Aesthetics**: The `...` bubble is the standard "loading/waiting" indicator and takes up minimal space reliably.