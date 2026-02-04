import unittest
from unittest.mock import MagicMock, patch

from tg_translator.translator_service import TranslatorService


class TestGroqTranslation(unittest.TestCase):
    def setUp(self):
        # Prevent actual API calls or model loading
        with patch("tg_translator.translator_service.os.getenv") as mock_env:
            mock_env.return_value = None  # No key initially
            self.service = TranslatorService()

        # Mock GoogleTranslator to avoid network calls
        self.google_patcher = patch("tg_translator.translator_service.GoogleTranslator")
        self.MockGoogleTranslator = self.google_patcher.start()

        # Setup supported languages for _get_language_name logic
        mock_gt_instance = self.MockGoogleTranslator.return_value
        mock_gt_instance.get_supported_languages.return_value = {
            "english": "en",
            "russian": "ru",
        }

    def tearDown(self):
        self.google_patcher.stop()
        self.service.shutdown()

    def test_get_language_name(self):
        """Test language code to name conversion."""
        self.assertEqual(self.service._get_language_name("en"), "english")
        self.assertEqual(self.service._get_language_name("ru"), "russian")
        self.assertEqual(self.service._get_language_name("unknown"), "unknown")

    def test_translate_groq_sync_success(self):
        """Test successful translation via Groq."""
        # Setup mock client
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="Translated Text"))
        ]
        mock_client.chat.completions.create.return_value = mock_completion

        self.service.groq_client = mock_client

        # Execute
        result = self.service._translate_groq_sync("Source", "en", "ru")

        # Verify
        self.assertEqual(result, "Translated Text")
        mock_client.chat.completions.create.assert_called_once()

        # Verify prompt construction (system message)
        args, kwargs = mock_client.chat.completions.create.call_args
        messages = kwargs["messages"]
        self.assertEqual(messages[0]["role"], "system")
        # Check that it converted 'en'->'english' and 'ru'->'russian'
        self.assertIn("english", messages[0]["content"].lower())
        self.assertIn("russian", messages[0]["content"].lower())
        self.assertEqual(messages[1]["content"], "Source")

    def test_translate_groq_sync_failure(self):
        """Test Groq failure returns None."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        self.service.groq_client = mock_client

        result = self.service._translate_groq_sync("Source", "en", "ru")
        self.assertIsNone(result)

    def test_translate_sync_uses_groq(self):
        """Test that _translate_sync prefers Groq when available."""
        # Mock _get_language_name to avoid extra GoogleTranslator calls
        self.service._get_language_name = MagicMock(side_effect=lambda x: x)

        # Setup Groq mock
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="Groq Translation"))
        ]
        mock_client.chat.completions.create.return_value = mock_completion
        self.service.groq_client = mock_client

        # Mock heuristic check (detecting source lang)
        mock_gt_instance = self.MockGoogleTranslator.return_value
        mock_gt_instance.translate.return_value = "Привет"
        # "Hello" (input) != "Привет" (primary ru check) -> Source is Secondary (en)

        result = self.service._translate_sync(
            "Hello", primary_lang="ru", secondary_lang="en"
        )

        self.assertEqual(result, "Groq Translation")
        mock_client.chat.completions.create.assert_called_once()

        # Ensure it didn't call GoogleTranslator for the FINAL translation
        # It was called once for heuristic check
        self.assertEqual(self.MockGoogleTranslator.call_count, 1)

    def test_translate_sync_fallback_on_groq_failure(self):
        """Test fallback to Google when Groq fails."""
        # Mock _get_language_name to avoid extra GoogleTranslator calls
        self.service._get_language_name = MagicMock(side_effect=lambda x: x)

        # Setup Groq failure
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Groq Down")
        self.service.groq_client = mock_client

        # Mock Google responses
        mock_gt_instance = self.MockGoogleTranslator.return_value
        # 1. Heuristic check: "Hello" -> "Привет" (implies source != primary)
        # 2. Final translation: "Hello" -> "Google Translation"
        mock_gt_instance.translate.side_effect = ["Привет", "Google Translation"]

        result = self.service._translate_sync(
            "Hello", primary_lang="ru", secondary_lang="en"
        )

        # Optimization: Since target ("ru") == primary ("ru") and text ("Hello") hasn't changed,
        # it returns the cached result "Привет" instead of calling Google again.
        self.assertEqual(result, "Привет")

        # Verify Groq was tried
        mock_client.chat.completions.create.assert_called_once()

        # Verify Google was called only once (for heuristic), avoiding redundant call
        self.assertEqual(self.MockGoogleTranslator.call_count, 1)
