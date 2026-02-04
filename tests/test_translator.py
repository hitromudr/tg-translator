import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tg_translator.translator_service import TranslatorService


class TestTranslatorService(unittest.TestCase):
    def setUp(self):
        self.service = TranslatorService()
        # Patch GoogleTranslator at the module level where it is imported
        self.patcher = patch("tg_translator.translator_service.GoogleTranslator")
        self.MockGoogleTranslator = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.service.shutdown()

    def test_normalize_language_code(self):
        # Setup mock for get_supported_languages used inside normalize_language_code
        # It creates a new GoogleTranslator() instance and calls get_supported_languages
        mock_gt_instance = self.MockGoogleTranslator.return_value
        mock_gt_instance.get_supported_languages.return_value = {
            "english": "en",
            "russian": "ru",
            "chinese (simplified)": "zh-CN",
            "ukrainian": "uk",
        }

        # Test valid codes
        self.assertEqual(self.service.normalize_language_code("en"), "en")
        self.assertEqual(self.service.normalize_language_code("EN"), "en")

        # Test aliases
        self.assertEqual(self.service.normalize_language_code("cn"), "zh-CN")
        self.assertEqual(self.service.normalize_language_code("ua"), "uk")

        # Test names
        self.assertEqual(self.service.normalize_language_code("English"), "en")
        self.assertEqual(self.service.normalize_language_code("russian"), "ru")

        # Test invalid
        self.assertIsNone(self.service.normalize_language_code("invalid"))
        self.assertIsNone(self.service.normalize_language_code(""))

    def test_translate_sync_direct_to_primary(self):
        """
        Test case where translation to primary language changes the text,
        meaning the source was NOT primary.
        """
        mock_instance = self.MockGoogleTranslator.return_value

        # Scenario: Input "Hello" (EN), Primary "ru".
        # 1. translate("Hello") to "ru" -> returns "Привет"
        # Since "Привет" != "Hello", it returns "Привет".

        mock_instance.translate.return_value = "Привет"

        result = self.service._translate_sync(
            "Hello", primary_lang="ru", secondary_lang="en"
        )

        self.assertEqual(result, "Привет")

        # Verify instantiation with target='ru'
        # Note: GoogleTranslator is instantiated multiple times.
        # We check if it was initialized with target='ru'
        self.MockGoogleTranslator.assert_any_call(source="auto", target="ru")

    def test_translate_sync_fallback_to_secondary_heuristic(self):
        """
        Test case where heuristic detects primary language (Cyrillic),
        so we skip the check and translate directly to secondary.
        """
        mock_instance = self.MockGoogleTranslator.return_value

        # Scenario: Input "Привет" (RU), Primary "ru", Secondary "en".
        # Heuristic sees "Привет" has Cyrillic -> is_source_primary = True.
        # Target = "en".
        # translate("Привет") to "en" -> returns "Hello".

        mock_instance.translate.return_value = "Hello"

        result = self.service._translate_sync(
            "Привет", primary_lang="ru", secondary_lang="en"
        )

        self.assertEqual(result, "Hello")

        # Verify calls
        # Should NOT init with target='ru' (skipped check)
        # Should init with target='en'
        self.MockGoogleTranslator.assert_called_with(source="auto", target="en")

    def test_translate_sync_fallback_no_heuristic(self):
        """
        Test fallback logic when heuristic doesn't apply (e.g. latin chars for RU primary).
        """
        mock_instance = self.MockGoogleTranslator.return_value

        # Scenario: Input "Hello" (EN). Primary "ru".
        # Heuristic: False.
        # Check: translate("Hello", target="ru") -> "Привет".
        # "Привет" != "Hello". is_source_primary = False.
        # Target = "ru".
        # Optimization catches it and returns "Привет".

        mock_instance.translate.return_value = "Привет"

        result = self.service._translate_sync(
            "Hello", primary_lang="ru", secondary_lang="en"
        )
        self.assertEqual(result, "Привет")
        # Should have checked 'ru'
        self.MockGoogleTranslator.assert_any_call(source="auto", target="ru")

    def test_dictionary_bug_regression(self):
        """
        Test that dictionary substitution doesn't break direction detection.
        Regression for task-015: "Апдейт" -> "update" -> "обновлять" (wrong).
        Should remain "update".
        """
        mock_instance = self.MockGoogleTranslator.return_value

        # Scenario:
        # User input: "Апдейт" (RU).
        # Dictionary changed it to: "update".
        # _translate_sync called with text="update", original_text="Апдейт".

        # Heuristic: "Апдейт" has Cyrillic. Primary="ru".
        # is_source_primary = True.
        # Target = "en".

        # Translation call: "update" -> "en" -> "update".

        mock_instance.translate.return_value = "update"

        result = self.service._translate_sync(
            text="update",
            primary_lang="ru",
            secondary_lang="en",
            original_text="Апдейт",
        )

        self.assertEqual(result, "update")

        # Verify it translated to EN, not RU
        self.MockGoogleTranslator.assert_called_with(source="auto", target="en")

    def test_translate_sync_optimization(self):
        """
        Test optimization: if target is primary and text hasn't changed, return result.
        """
        mock_instance = self.MockGoogleTranslator.return_value
        # 1. translate("Text") to "ru" -> "Translated"
        # "Translated" != "Text" -> is_source_primary = False
        # target_lang = "ru" (primary)
        # Optimization: target_lang == primary AND text == sample_text -> return res_prim ("Translated")

        mock_instance.translate.return_value = "Translated"

        result = self.service._translate_sync(
            "Text", primary_lang="ru", secondary_lang="en"
        )
        self.assertEqual(result, "Translated")

        # Should only call translate once effectively (or at least logic flow uses the first result)
        self.assertEqual(mock_instance.translate.call_count, 1)

    def test_translate_sync_error(self):
        mock_instance = self.MockGoogleTranslator.return_value
        mock_instance.translate.side_effect = Exception("API Error")

        result = self.service._translate_sync("Hello")
        self.assertIsNone(result)


class TestTranslatorServiceAsync(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = TranslatorService()
        # Mock the internal executor to run synchronously or mock _translate_sync directly
        # For unit testing translate_message, it's better to mock _translate_sync
        # to avoid spawning threads and mocking GoogleTranslator again.
        self.service._translate_sync = MagicMock()  # type: ignore

    async def asyncTearDown(self):
        self.service.shutdown()

    async def test_translate_message_empty(self):
        result = await self.service.translate_message("")
        self.assertIsNone(result)

        result = await self.service.translate_message("   ")
        self.assertIsNone(result)

    async def test_translate_message_defaults(self):
        """Test translation without DB (using defaults)"""
        self.service._translate_sync.return_value = "Translated"

        result = await self.service.translate_message("Source")

        self.assertEqual(result, "Translated")
        self.service._translate_sync.assert_called_with("Source", "ru", "en", "Source")

    async def test_translate_message_with_db(self):
        """Test translation with DB settings"""
        mock_db = MagicMock()
        mock_db.get_languages.return_value = ("es", "fr")
        mock_db.get_terms.return_value = []  # No custom terms

        self.service.db = mock_db
        self.service._translate_sync.return_value = "Translated"

        result = await self.service.translate_message("Source", chat_id=123)

        self.assertEqual(result, "Translated")
        mock_db.get_languages.assert_called_with(123)
        self.service._translate_sync.assert_called_with("Source", "es", "fr", "Source")

    async def test_translate_message_with_custom_dict(self):
        """Test custom dictionary replacement before translation"""
        mock_db = MagicMock()
        mock_db.get_languages.return_value = ("ru", "en")
        # Custom term: "foo" -> "bar"
        mock_db.get_terms.return_value = [("foo", "bar")]

        self.service.db = mock_db
        self.service._translate_sync.return_value = "Translated"

        # Input text contains "foo"
        await self.service.translate_message("This is foo test", chat_id=123)

        # Check that _translate_sync was called with modified text
        # "This is foo test" -> "This is bar test"
        self.service._translate_sync.assert_called_with(
            "This is bar test", "ru", "en", "This is foo test"
        )
