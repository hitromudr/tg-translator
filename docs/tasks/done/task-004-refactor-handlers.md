# Refactor: Modularize Bot Handlers

**Status**: Backlog
**ID**: task-004

## Description
The `src/tg_translator/main.py` file has grown too large (~600 lines) and currently mixes application initialization, configuration, command handlers, and business logic. This violates the Single Responsibility Principle and makes the codebase difficult to maintain, test, and extend.

## Goals
1.  Create a new Python package `src/tg_translator/handlers/`.
2.  Refactor and move existing command handlers into dedicated modules:
    -   `cmd_start.py` (start, help)
    -   `cmd_dictionary.py` (dict command)
    -   `cmd_settings.py` (lang command)
    -   `cmd_utils.py` (clean command)
    -   `msg_text.py` (text translation logic)
    -   `msg_voice.py` (voice handling logic)
    -   `callback_tts.py` (TTS callbacks)
3.  Update `main.py` to strictly handle:
    -   Environment configuration (`dotenv`).
    -   Bot application building (`ApplicationBuilder`).
    -   Handler registration.
    -   Startup/Shutdown logic.
4.  Ensure all tests still pass after refactoring.

## Benefits
-   **Testability**: Easier to unit test individual handlers without mocking the entire Application.
-   **Scalability**: New features (like Inline mode) can be added as new modules without cluttering `main.py`.
-   **Readability**: Clearer project structure for new developers.

## Technical Details
-   Need to ensure the `TranslatorService` singleton or dependency is correctly passed to handlers (either via `context.bot_data` or dependency injection).