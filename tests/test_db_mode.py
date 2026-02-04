import os
import tempfile
import unittest

from tg_translator.db import Database


class TestDatabaseMode(unittest.TestCase):
    def setUp(self):
        # Use a temporary file to persist state across multiple connections
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db = Database(self.db_path)

    def tearDown(self):
        os.close(self.db_fd)
        os.remove(self.db_path)

    def test_default_mode(self):
        """Test that a new chat has 'auto' mode by default."""
        # Querying a non-existent chat should return default
        mode = self.db.get_mode(12345)
        self.assertEqual(mode, "auto")

    def test_set_get_mode(self):
        """Test setting and retrieving modes."""
        chat_id = 67890

        # Initial check
        self.assertEqual(self.db.get_mode(chat_id), "auto")

        # Set to manual
        success = self.db.set_mode(chat_id, "manual")
        self.assertTrue(success, "Failed to set mode to manual")
        self.assertEqual(self.db.get_mode(chat_id), "manual")

        # Set back to auto
        success = self.db.set_mode(chat_id, "auto")
        self.assertTrue(success, "Failed to set mode to auto")
        self.assertEqual(self.db.get_mode(chat_id), "auto")

        # Set to interactive (future proofing)
        success = self.db.set_mode(chat_id, "interactive")
        self.assertTrue(success)
        self.assertEqual(self.db.get_mode(chat_id), "interactive")

    def test_persistence_mixed_with_languages(self):
        """Test that mode works correctly alongside language settings."""
        chat_id = 111222

        # 1. Set languages
        self.db.set_languages(chat_id, "fr", "de")

        # 2. Check default mode is still auto
        self.assertEqual(self.db.get_mode(chat_id), "auto")

        # 3. Change mode
        self.db.set_mode(chat_id, "manual")

        # 4. Verify languages are preserved
        self.assertEqual(self.db.get_languages(chat_id), ("fr", "de"))

        # 5. Verify mode is preserved
        self.assertEqual(self.db.get_mode(chat_id), "manual")

    def test_voice_gender(self):
        """Test setting and retrieving voice gender."""
        chat_id = 999

        # Default should be male
        self.assertEqual(self.db.get_voice_gender(chat_id), "male")

        # Set to female
        success = self.db.set_voice_gender(chat_id, "female")
        self.assertTrue(success)
        self.assertEqual(self.db.get_voice_gender(chat_id), "female")

        # Set back to male
        self.db.set_voice_gender(chat_id, "male")
        self.assertEqual(self.db.get_voice_gender(chat_id), "male")

        # Invalid gender should fail
        success = self.db.set_voice_gender(chat_id, "robot")
        self.assertFalse(success)
        self.assertEqual(self.db.get_voice_gender(chat_id), "male")


if __name__ == "__main__":
    unittest.main()
