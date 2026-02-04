# Fix: TTS Spam & English Voice Gender

**Status**: In Progress
**ID**: task-021

## Description
1.  **Spam Issue**: The user reported receiving multiple voice messages for a single "Speak" button click. This is likely due to the user clicking multiple times because there was no immediate visual feedback during the TTS generation delay (Silero takes 1-3 seconds).
2.  **Voice Gender Issue**: The user reported that voice gender settings might not be persisting correctly when switching languages (specifically to English). We need to verify the speaker mapping for English models.

## Goals
1.  **UX Improvement (Debounce)**:
    -   In `handlers/callback_tts.py`, immediately acknowledge the button click using `query.answer("🔊 Generating audio...")`. This provides instant feedback, reducing the urge to spam-click.
    -   (Optional) Use a simple in-memory set to prevent concurrent generation requests for the same message ID? (Simpler: just the feedback usually solves it).

2.  **Voice Mapping Refinement**:
    -   Verify Silero `v3_en` speakers. `en_0` is technically male, but might sound neutral.
    -   Update mapping to more distinct voices if possible (e.g., test `en_2` or others for male, `en_1` or `en_10` for female).
    -   Double-check that `gender` parameter is correctly passed from DB to `generate_audio`.

## Technical Details
-   **File**: `src/tg_translator/handlers/callback_tts.py`
-   **File**: `src/tg_translator/translator_service.py`

## Benefits
-   **Stability**: Prevents accidental bot spam.
-   **Quality**: Ensures the user gets the voice personality they selected.