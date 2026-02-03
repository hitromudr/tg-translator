import logging
import sqlite3
import uuid
from typing import List, Optional, Tuple, cast

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "dictionary.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Create a new database connection.
        Using a new connection per operation is thread-safe and robust for SQLite.
        """
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Initialize the database schema and migrate if necessary."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Create settings table for language pairs
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        chat_id INTEGER PRIMARY KEY,
                        primary_lang TEXT NOT NULL DEFAULT 'ru',
                        secondary_lang TEXT NOT NULL DEFAULT 'en'
                    )
                    """)

                # 2. Create exports table for dictionary sharing
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS exports (
                        code TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """)

                # 3. Manage dictionary table (Migration logic)
                # Check if dictionary table exists
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='dictionary'"
                )
                if not cursor.fetchone():
                    # Create new table
                    cursor.execute("""
                        CREATE TABLE dictionary (
                            chat_id INTEGER NOT NULL,
                            lang_pair TEXT NOT NULL DEFAULT 'ru-en',
                            source_term TEXT NOT NULL,
                            target_term TEXT NOT NULL,
                            PRIMARY KEY (chat_id, lang_pair, source_term)
                        )
                        """)
                else:
                    # Table exists, check if migration needed (add lang_pair)
                    cursor.execute("PRAGMA table_info(dictionary)")
                    columns = [info[1] for info in cursor.fetchall()]
                    if "lang_pair" not in columns:
                        logger.info("Migrating dictionary: adding lang_pair column...")
                        # SQLite requires recreation for primary key changes
                        cursor.execute(
                            "ALTER TABLE dictionary RENAME TO dictionary_old"
                        )
                        cursor.execute("""
                            CREATE TABLE dictionary (
                                chat_id INTEGER NOT NULL,
                                lang_pair TEXT NOT NULL DEFAULT 'ru-en',
                                source_term TEXT NOT NULL,
                                target_term TEXT NOT NULL,
                                PRIMARY KEY (chat_id, lang_pair, source_term)
                            )
                            """)
                        # Copy old data, defaulting to 'ru-en'
                        cursor.execute("""
                            INSERT INTO dictionary (chat_id, lang_pair, source_term, target_term)
                            SELECT chat_id, 'ru-en', source_term, target_term FROM dictionary_old
                            """)
                        cursor.execute("DROP TABLE dictionary_old")

                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    # --- Dictionary Methods ---

    def add_term(
        self, chat_id: int, source: str, target: str, lang_pair: str = "ru-en"
    ) -> bool:
        """
        Add or update a translation term for a specific chat and language pair.
        """
        try:
            source_lower = source.strip().lower()
            target_clean = target.strip()
            lang_pair = lang_pair.strip().lower()

            if not source_lower or not target_clean:
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO dictionary (chat_id, lang_pair, source_term, target_term)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chat_id, lang_pair, source_lower, target_clean),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding term: {e}")
            return False

    def remove_term(self, chat_id: int, source: str, lang_pair: str = "ru-en") -> bool:
        """Remove a term from the dictionary for a specific language pair."""
        try:
            source_lower = source.strip().lower()
            lang_pair = lang_pair.strip().lower()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM dictionary
                    WHERE chat_id = ? AND source_term = ? AND lang_pair = ?
                    """,
                    (chat_id, source_lower, lang_pair),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing term: {e}")
            return False

    def get_terms(
        self, chat_id: int, lang_pair: str = "ru-en"
    ) -> List[Tuple[str, str]]:
        """
        Retrieve all dictionary terms for a chat and language pair.
        """
        try:
            lang_pair = lang_pair.strip().lower()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT source_term, target_term
                    FROM dictionary
                    WHERE chat_id = ? AND lang_pair = ?
                    """,
                    (chat_id, lang_pair),
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching terms: {e}")
            return []

    # --- Settings Methods ---

    def set_languages(self, chat_id: int, primary: str, secondary: str) -> bool:
        """Set language pair for a chat."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO settings (chat_id, primary_lang, secondary_lang)
                    VALUES (?, ?, ?)
                    """,
                    (chat_id, primary, secondary),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting languages: {e}")
            return False

    def get_languages(self, chat_id: int) -> Tuple[str, str]:
        """Get language pair for a chat. Returns ('ru', 'en') by default."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT primary_lang, secondary_lang
                    FROM settings
                    WHERE chat_id = ?
                    """,
                    (chat_id,),
                )
                row = cursor.fetchone()
                if row:
                    return cast(Tuple[str, str], row)
                return ("ru", "en")
        except Exception as e:
            logger.error(f"Error fetching languages: {e}")
            return ("ru", "en")

    # --- Import/Export Methods ---

    def create_export(self, data: str) -> Optional[str]:
        """Create a temporary export code for dictionary data."""
        try:
            code = f"DICT-{uuid.uuid4().hex[:6].upper()}"
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO exports (code, data)
                    VALUES (?, ?)
                    """,
                    (code, data),
                )
                conn.commit()
            return code
        except Exception as e:
            logger.error(f"Error creating export: {e}")
            return None

    def get_export(self, code: str) -> Optional[str]:
        """Retrieve export data by code."""
        try:
            # Clean up old exports (older than 24h)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM exports WHERE created_at < datetime('now', '-1 day')"
                )

                cursor.execute(
                    "SELECT data FROM exports WHERE code = ?", (code.upper(),)
                )
                row = cursor.fetchone()
                if row:
                    return cast(str, row[0])
                return None
        except Exception as e:
            logger.error(f"Error fetching export: {e}")
            return None
