# Feature: Advanced Voice Control & Presets

**Status**: In Progress
**ID**: task-022

## Description
Currently, users can only switch between generic "Male" and "Female" genders. For English (Silero v3), there are 118 speakers (`en_0`...`en_117`), but users are stuck with the hardcoded default (`en_2`). Users want to explore available voices, test them, and assign specific speakers to specific languages and genders per chat.

## Goals
1.  **Database Update**:
    -   Create `voice_presets` table: `chat_id`, `lang_code`, `gender`, `speaker_name`.
    -   Add methods `set_voice_preset` and `get_voice_preset`.

2.  **Command Expansion (`/voice`)**:
    -   `/voice test <lang> <speaker>`: Generates a sample audio using the specified speaker (e.g., `/voice test en en_45`).
    -   `/voice set <lang> <gender> <speaker>`: Saves the preference (e.g., `/voice set en male en_45`).
    -   `/voice reset`: Clears custom presets for the chat.

3.  **TTS Logic Update**:
    -   Update `TranslatorService.generate_audio` (and internal `_generate_audio_silero_sync`) to accept `chat_id` (or look up presets).
    -   Logic: Check DB for a custom preset for `(chat_id, lang, gender)`. If found, use that speaker. If not, use the hardcoded default.

## Technical Details
-   **Silero Speakers**:
    -   RU (`v4_ru`): `aidar`, `baya`, `kseniya`, `xenia`, `eugene`, `random`.
    -   UA (`v4_ua`): `mykyta`.
    -   EN (`v3_en`): `en_0` ... `en_117`.
-   **Test Phrase**: "This is a test of the selected voice." (localized for RU/UA).

## Benefits
-   **Customization**: Users can find the perfect voice for their chat.
-   **Discovery**: Exposes the full power of the Silero English model (118 voices).