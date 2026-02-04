# Task: Multi-language Support

## Status
- [ ] In Progress

## Description
Enable custom language configuration per chat. Currently, the bot is hardcoded to switch between Russian and English. We need to allow users to define their own language pairs (e.g., Russian <-> Serbian, English <-> Spanish).

## Requirements
1.  **Database**:
    - New table `settings` (or `chat_settings`).
    - Columns: `chat_id` (PK), `primary_lang` (default 'ru'), `secondary_lang` (default 'en').
2.  **Bot Commands**:
    - `/lang set <lang1> <lang2>`: Set the language pair for the chat.
    - `/lang status`: Show current language settings.
    - `/lang reset`: Reset to default (ru-en).
3.  **Translation Logic**:
    - Replace hardcoded `_is_cyrillic` check with dynamic language detection where possible, or simplistic 2-way toggle.
    - **Strategy**:
        - Detect source language (Google Translate API usually returns this).
        - If source is close to `primary_lang` -> Target is `secondary_lang`.
        - If source is close to `secondary_lang` -> Target is `primary_lang`.
        - Else -> Target is `primary_lang`.

## Implementation Plan

### 1. Database Update (`src/tg_translator/db.py`)
- Add `create_settings_table`.
- Add methods: `set_languages(chat_id, l1, l2)`, `get_languages(chat_id)`.

### 2. Service Update (`src/tg_translator/translator_service.py`)
- Update `translate_message` to fetch lang settings.
- Refactor `_translate_sync`:
    - Fetch chat settings.
    - Use dynamic source/target.
    - **Note**: `GoogleTranslator` object creation is lightweight, can be done on the fly.

### 3. Command Handlers (`src/tg_translator/main.py`)
- Add `/lang` command handler.
- Validate language codes (simple check if code is 2 chars).

### 4. Testing
- Unit tests for DB settings.
- Integration test for switching languages.