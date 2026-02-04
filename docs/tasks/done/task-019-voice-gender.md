# Feature: Voice Gender Selection

**Status**: In Progress
**ID**: task-019

## Description
Users want the ability to choose the gender of the TTS voice. Currently, the bot uses hardcoded defaults (e.g., 'kseniya' for RU). We will implement a setting to toggle between Male and Female voices.

## Goals
1.  **Database Update**:
    -   Add `voice_gender` column to `settings` table (TEXT, Default 'male').
    -   Update `set_voice_gender` and `get_voice_gender` methods in `Database`.

2.  **Command Implementation**:
    -   `/voice [male|female]`: Sets the preferred voice gender for the chat.
    -   `/voice status`: Shows current setting.

3.  **TTS Logic Update (`TranslatorService`)**:
    -   Update `_generate_audio_silero_sync` to accept a `gender` argument.
    -   Implement speaker mapping:
        -   **RU**: Male=`aidar`, Female=`kseniya`
        -   **EN**: Male=`en_0`, Female=`en_1` (or similar)
        -   **UA**: Male=`mykyta`, Female=`mykyta` (Fallback to male if female model unavailable in v4, or check for `lada`).

4.  **Handler Integration**:
    -   In `handlers/callback_tts.py` and `handlers/callback_translate.py` (Speak button), fetch the chat's voice preference from DB before generating audio.

## Technical Details
-   **Default**: 'male' (to differentiate from the previous gTTS default).
-   **Scope**: Per-chat setting (stored in `settings` table).

## Benefits
-   **Personalization**: Users can choose the voice that sounds best to them.
-   **Variety**: Breaks the monotony of a single voice.