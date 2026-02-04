# Fix: Shorten Translate Button Text for Mobile

**Status**: In Progress
**ID**: task-013

## Description
On mobile devices with narrower screens, the button label "Translate" is truncated (cut off) when displayed side-by-side with the "Text" button for voice messages.

## Goals
1.  **Update Button Label**:
    -   Change `[ 🌐 Translate ]` to `[ 🌐 Transl. ]` *only* in the voice message interactive mode (where two buttons share the row).
    -   Keep the full `[ 🌐 Translate ]` label for text messages (single button row).

## Technical Details
-   Modify `src/tg_translator/handlers/translation.py`.
-   Modify `src/tg_translator/handlers/callback_translate.py` (specifically in the `transcribe_this` action where buttons might be re-rendered).

## Benefits
-   **UI/UX**: Prevents ugly text truncation on mobile clients.