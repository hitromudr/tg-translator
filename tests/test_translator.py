import unittest
from unittest.mock import MagicMock, patch

from tg_translator.translator_service import TranslatorService


class TestTranslatorService(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("tg_translator.translator_service.GoogleTranslator")
        self.MockGoogleTranslator = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_is_cyrillic(self):
        service = TranslatorService()
        self.assertTrue(service._is_cyrillic("Привет"))
        self.assertFalse(service._is_cyrillic("Hello"))
        self.assertTrue(service._is_cyrillic("Mix Привет"))
        self.assertFalse(service._is_cyrillic("123"))
        service.shutdown()

    def test_translate_sync_to_english(self):
        service = TranslatorService()
        # Manually inject mocks for the translators
        mock_to_en = MagicMock()
        mock_to_ru = MagicMock()
        service._to_en = mock_to_en
        service._to_ru = mock_to_ru

        mock_to_en.translate.return_value = "Hello"

        # Test Cyrillic input -> Should trigger to_en
        result = service._translate_sync("Привет")
        self.assertEqual(result, "Hello")
        mock_to_en.translate.assert_called_with("Привет")
        mock_to_ru.translate.assert_not_called()
        service.shutdown()

    def test_translate_sync_to_russian(self):
        service = TranslatorService()
        mock_to_en = MagicMock()
        mock_to_ru = MagicMock()
        service._to_en = mock_to_en
        service._to_ru = mock_to_ru

        mock_to_ru.translate.return_value = "Привет"

        # Test Latin input -> Should trigger to_ru
        result = service._translate_sync("Hello")
        self.assertEqual(result, "Привет")
        mock_to_ru.translate.assert_called_with("Hello")
        mock_to_en.translate.assert_not_called()
        service.shutdown()

    def test_translate_sync_error(self):
        service = TranslatorService()
        mock_to_ru = MagicMock()
        service._to_ru = mock_to_ru

        mock_to_ru.translate.side_effect = Exception("API Error")

        result = service._translate_sync("Hello")
        self.assertIsNone(result)
        service.shutdown()


class TestTranslatorServiceAsync(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.patcher = patch("tg_translator.translator_service.GoogleTranslator")
        self.MockGoogleTranslator = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    async def test_translate_message(self):
        service = TranslatorService()

        # Mock _translate_sync to isolate async logic
        service._translate_sync = MagicMock(return_value="Translated")

        result = await service.translate_message("Source")
        self.assertEqual(result, "Translated")
        service._translate_sync.assert_called_with("Source")

        service.shutdown()

    async def test_translate_message_empty(self):
        service = TranslatorService()
        result = await service.translate_message("")
        self.assertIsNone(result)

        result = await service.translate_message("   ")
        self.assertIsNone(result)
        service.shutdown()
