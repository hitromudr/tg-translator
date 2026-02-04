# Feature: Dynamic Language Labels for Buttons

**Status**: In Progress
**ID**: task-014

## Description
Currently, the buttons show a static label "Translate" or "Transl.". The user requested that the bot show the target languages instead. For text messages, we can guess the direction. For voice messages (before transcription), we should show the configured language pair.

## Goals
1.  **Voice Messages (Unknown Content)**:
    -   Fetch current language pair from DB (e.g., `ru`, `en`).
    -   Label the translate button as `[ 🌐 RU/EN ]` (uppercase codes).

2.  **Text Messages (Known Content)**:
    -   Analyze the text using simple heuristics (e.g., regex for Cyrillic).
    -   If text appears to be Primary Language (e.g., Russian) -> Label: `[ 🌐 to EN ]`.
    -   If text appears to be Secondary Language (e.g., English) -> Label: `[ 🌐 to RU ]`.

## Technical Details
-   **Handlers**: Update `src/tg_translator/handlers/translation.py`.
-   **Logic**:
    -   Retrieve `l1, l2` using `db.get_languages(chat_id)`.
    -   Use `re.search(r"[а-яА-ЯёЁ]", text)` to determine direction for text messages.
-   **Formatting**: ensure language codes are `.upper()`.

## Benefits
-   **Information**: User knows immediately which languages are active.
-   **Confidence**: For text, user sees that the bot correctly identified the source language direction before clicking.