# Task: Text-to-Speech (TTS) Support

## Status
- [ ] In Progress

## Description
Add the ability to listen to the pronunciation of the translated text. This is useful for language learning and accessibility. We will use the Google Text-to-Speech (gTTS) library to generate audio on demand.

## Requirements
1.  **Library**: Use `gTTS` (Google Text-to-Speech) for audio generation.
2.  **UX**:
    - Attach an **Inline Keyboard Button** (e.g., "🔊") to every translation message.
    - When clicked, the bot should reply with a Voice message containing the spoken text.
3.  **Performance**:
    - Generate audio only when requested (lazy loading) to save bandwidth and API calls.
    - Use temporary files for MP3s and clean them up immediately.

## Implementation Plan

### 1. Dependencies (`pyproject.toml`)
- Add `gTTS`.

### 2. Service Layer (`src/tg_translator/translator_service.py`)
- Add method `generate_audio(text, lang_code) -> file_path`.
- Ensure it runs in a thread pool (blocking I/O).

### 3. Bot Logic (`src/tg_translator/main.py`)
- Update `handle_message`: Add `InlineKeyboardMarkup` with a callback data containing a hash or reference to the text (or just `speak`).
    - *Constraint*: Callback data has a 64-byte limit. We can't store the whole text there.
    - *Solution*: Since we reply to the original message, we can't easily reference the *translation* text in the callback unless we store it.
    - *Alternative Strategy*: The button is attached to the *Bot's* message (the translation). When clicked, we can read the text of the message the button is attached to (`update.callback_query.message.text`). However, our translations are hidden in spoilers `||...||`. We need to strip the spoiler tags before sending to TTS.

### 4. Handler
- Add `CallbackQueryHandler` for the `speak` action.