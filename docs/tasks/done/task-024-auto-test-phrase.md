# Feature: Auto-Translated Test Phrases & Expanded Silero Support

**Status**: In Progress
**ID**: task-024

## Description
Currently, the `/voice test` command relies on a hardcoded dictionary of test phrases. If a user tests a language not in this map (e.g., Polish), the bot sends English text to the TTS engine, resulting in poor audio (English words read with foreign pronunciation). Maintaining a hardcoded list for 100+ languages is inefficient.

Additionally, Silero TTS supports German, Spanish, and French, but our current implementation falls back to the robotic `gTTS` for these languages because they are not mapped in `TranslatorService`.

## Goals
1.  **Auto-Translation for Voice Test**:
    -   In `handlers/admin.py`, if a language is not in the hardcoded map (RU/UA/EN), use `TranslatorService` to translate the phrase "This is a test of the selected voice" into the target language on the fly.
    -   This ensures correct pronunciation for *any* supported language (e.g., Polish, Chinese, Arabic).

2.  **Expand Silero Support**:
    -   Update `TranslatorService` to map `de`, `es`, and `fr` to their respective Silero v3 models.
    -   **German**: `v3_de` (Speaker: `thorsten`).
    -   **Spanish**: `v3_es` (Speaker: `es_0` / `tux`).
    -   **French**: `v3_fr` (Speakers: `fr_0`...`fr_5`).

## Technical Details
-   **File**: `src/tg_translator/handlers/admin.py`
    -   Use `service.translate_message("This is a test...", target_lang=lang)` logic inside `voice_command`.
-   **File**: `src/tg_translator/translator_service.py`
    -   Add `elif lang_code == 'de': ...` etc. inside `_generate_audio_silero_sync`.
    -   Determine default speakers for new languages.

## Benefits
-   **Scalability**: `/voice test` works correctly for all 100+ Google Translate languages without manual updates.
-   **Quality**: High-quality neural TTS for German, Spanish, and French users.