import logging
import sqlite3
from typing import List, Tuple

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
        """Initialize the database schema."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dictionary (
                        chat_id INTEGER NOT NULL,
                        source_term TEXT NOT NULL,
                        target_term TEXT NOT NULL,
                        PRIMARY KEY (chat_id, source_term)
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def add_term(self, chat_id: int, source: str, target: str) -> bool:
        """
        Add or update a translation term for a specific chat.
        source is stored in lowercase for case-insensitive matching logic.
        """
        try:
            # Normalize source to lowercase for case-insensitive lookup storage.
            # The target retains its case.
            source_lower = source.strip().lower()
            target_clean = target.strip()

            if not source_lower or not target_clean:
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO dictionary (chat_id, source_term, target_term)
                    VALUES (?, ?, ?)
                    """,
                    (chat_id, source_lower, target_clean),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding term: {e}")
            return False

    def remove_term(self, chat_id: int, source: str) -> bool:
        """Remove a term from the dictionary."""
        try:
            source_lower = source.strip().lower()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM dictionary
                    WHERE chat_id = ? AND source_term = ?
                    """,
                    (chat_id, source_lower),
                )
                conn.commit()
                # Check if any row was deleted
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing term: {e}")
            return False

    def get_terms(self, chat_id: int) -> List[Tuple[str, str]]:
        """
        Retrieve all dictionary terms for a chat.
        Returns a list of (source, target) tuples.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT source_term, target_term
                    FROM dictionary
                    WHERE chat_id = ?
                    """,
                    (chat_id,),
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching terms: {e}")
            return []
