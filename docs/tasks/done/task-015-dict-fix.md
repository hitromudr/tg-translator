# Bug: Dictionary Substitution Breaks Language Detection

**Status**: In Progress
**ID**: task-015

## Description
When a user adds a term to the dictionary (e.g., `Апдейт` -> `update`), the bot sometimes produces incorrect translations for that term (e.g., `обновлять` instead of `update`).

This happens because the **language direction detection** logic in `TranslatorService` might fail for single words, especially when the dictionary has already modified the text passed to the final translation step.

**Scenario:**
1. User input: `Апдейт` (Russian).
2. Dictionary replaces `Апдейт` -> `update` (English).
3. Bot attempts to determine translation direction.
   - It checks `original_text` ("Апдейт").
   - It tries translating "Апдейт" to Primary Language (RU).
   - **Failure Point**: If Google Translate returns something other than "Апдейт" (e.g. latinized "Update" or a correction), the bot concludes the source is **NOT** Russian.
4. Bot assumes source is Secondary (English) and sets Target to Primary (Russian).
5. Bot translates the modified text `update` to Russian -> `обновлять`.

## Goals
1.  **Improve Language Detection**:
    -   Modify `src/tg_translator/translator_service.py`.
    -   In `_translate_sync`, refine the logic for determining `is_source_primary`.
    -   Implement a **Character-set Heuristic** as a priority check:
        -   If `primary_lang` is Cyrillic (ru, uk, etc.) and `original_text` contains Cyrillic characters -> Assume Source is Primary.
        -   Only fall back to the "translation check" strategy if the heuristic is inconclusive (e.g., numbers, mixed text).

2.  **Verify Dictionary Flow**:
    -   Ensure `original_text` is correctly passed through `translate_message` to `_translate_sync`.

3.  **Test**:
    -   Create a test case reproducing the `Апдейт` -> `update` -> `обновлять` issue.
    -   Verify the fix prevents the back-translation.

## Technical Details
-   **Regex Heuristic**: `bool(re.search(r"[а-яА-ЯёЁ]", text))` is already used in other parts of the app. It should be centralized or reused in `_translate_sync` to lock the direction to `Primary -> Secondary` when Cyrillic is detected in the original text (assuming Primary is RU).

## Benefits
-   Dictionary replacements will work reliably.
-   Prevents "ping-pong" translation errors for single words.