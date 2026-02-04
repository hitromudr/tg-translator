# Fix Broken Unit Tests

**Status**: In Progress
**ID**: fix-002

## Description
The current unit tests in `tests/test_translator.py` are failing significantly. They reference methods that no longer exist (e.g., `_is_cyrillic`) and make assertions on mocks that do not match the current implementation of `TranslatorService`. Additionally, `mypy` is reporting type errors in `main.py`.

## Goals
1. Analyze the specific discrepancies between `tests/test_translator.py` and `src/tg_translator/translator_service.py`.
2. Update `tests/test_translator.py` to correctly test the current logic:
    - Remove/Update tests for `_is_cyrillic` (likely replaced by language detection logic).
    - Update `_translate_sync` tests to handle the new flow.
    - Fix async test mocks.
3. Address `mypy` type checking errors found in `src/tg_translator/main.py` regarding `MaybeInaccessibleMessage`.
4. Verify all tests pass with `make test`.

## Context
- `make test` output shows 5 failures in `test_translator.py`.
- `make lint` shows `mypy` errors related to `MaybeInaccessibleMessage` optional attributes not being safely accessed.