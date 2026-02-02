# Task: Custom Dictionary Support

## Status
- [x] Completed

## Description
Implement a custom dictionary feature that allows users to define specific translations for words or phrases within a chat. This is particularly useful for names (e.g., "Ian") or technical terms that the translation API misinterprets.

## Requirements
1.  **Persistence**: Use SQLite to store dictionary entries associated with `chat_id`.
2.  **Commands**:
    - `/dict add <original> <translation>`: Add or update a translation pair.
    - `/dict remove <original>`: Remove a translation pair.
    - `/dict list`: Show all custom translations for the current chat.
3.  **Integration**:
    - Modify the translation pipeline to apply these custom rules.
    - The most effective strategy for names is likely **pre-processing substitution** (replacing the term in the source text before sending it to the API) or **post-processing** if the API supports glossaries (Deep Translator/Google Free API likely doesn't support glossaries natively, so regex replacement is the way to go).

## Implementation Plan

### 1. Database Layer (`src/tg_translator/db.py`)
- Create a `Database` class using `sqlite3` or `aiosqlite`.
- Table `dictionary`: `chat_id` (INT), `source_term` (TEXT), `target_term` (TEXT).
- Methods: `add_term`, `remove_term`, `get_terms(chat_id)`.

### 2. Dictionary Logic
- Implement logic to fetch terms for a chat.
- Implement a `DictionaryProcessor` that applies replacements.
    - **Strategy**: Sort terms by length (descending) to avoid partial matches. Use regex with word boundaries `\b` to replace safely.

### 3. Bot Commands (`src/tg_translator/main.py`)
- Add handlers for `/dict`.
- Validate input (ensure both source and target are provided for add).
- Authorization: Strictly speaking, anyone in the chat can modify it for now, or restrict to admins (keep simple for v1).

### 4. Integration with `TranslatorService`
- Inject `DictionaryProcessor` or `Database` into `TranslatorService`.
- Before `_translate_sync`, apply substitutions.

### 5. Testing
- Unit tests for DB operations.
- Unit tests for string replacement logic (case sensitivity, substrings).

## Technical Notes
- **Case Sensitivity**: Users might want "Ian" -> "Иэн", but "ian" might be a different word (suffix?). For names, case-insensitive match might be safer, but case-sensitive is more precise. Let's start with case-insensitive for the *key* lookup, but replace with the provided casing.
- **Regex**: Use `re.IGNORECASE`.
