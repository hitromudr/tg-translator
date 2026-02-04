import unittest
from unittest.mock import MagicMock, mock_open, patch

from tg_translator.translator_service import TranslatorService


class TestGroqSTT(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Prevent actual API calls or model loading
        with patch("tg_translator.translator_service.os.getenv") as mock_env:
            mock_env.return_value = None
            self.service = TranslatorService()

        # Mock AudioSegment to avoid real file operations
        self.audio_patcher = patch("tg_translator.translator_service.AudioSegment")
        self.MockAudioSegment = self.audio_patcher.start()

    def tearDown(self):
        self.audio_patcher.stop()
        self.service.shutdown()

    def test_transcribe_groq_sync_success(self):
        """Test successful transcription via Groq."""
        # Setup mock client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Transcribed text"
        mock_client.audio.transcriptions.create.return_value = mock_response

        self.service.groq_client = mock_client

        # Mock file open
        m = mock_open(read_data=b"audio data")
        with patch("builtins.open", m):
            result = self.service._transcribe_groq_sync("test.ogg")

        self.assertEqual(result, "Transcribed text")

        # Verify conversion was called
        self.MockAudioSegment.from_ogg.assert_called_with("test.ogg")
        self.MockAudioSegment.from_ogg.return_value.export.assert_called()

        # Verify API call
        mock_client.audio.transcriptions.create.assert_called_once()
        args, kwargs = mock_client.audio.transcriptions.create.call_args
        self.assertEqual(kwargs["model"], "whisper-large-v3")

    def test_transcribe_groq_sync_failure(self):
        """Test Groq failure returns None."""
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
        self.service.groq_client = mock_client

        m = mock_open(read_data=b"audio data")
        with patch("builtins.open", m):
            result = self.service._transcribe_groq_sync("test.ogg")

        self.assertIsNone(result)

    @patch("tg_translator.translator_service.TranslatorService._transcribe_sync")
    async def test_transcribe_audio_uses_groq(self, mock_local_transcribe):
        """Test that transcribe_audio prefers Groq when available."""
        # Setup Groq mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Groq Result"
        mock_client.audio.transcriptions.create.return_value = mock_response
        self.service.groq_client = mock_client

        # Mock file IO
        m = mock_open(read_data=b"data")
        with patch("builtins.open", m):
            result = await self.service.transcribe_audio("test.ogg")

        self.assertEqual(result, "Groq Result")

        # Verify local Whisper was NOT called
        mock_local_transcribe.assert_not_called()

    @patch("tg_translator.translator_service.TranslatorService._transcribe_sync")
    async def test_transcribe_audio_fallback(self, mock_local_transcribe):
        """Test fallback to local Whisper when Groq fails."""
        # Setup Groq failure
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = Exception("Fail")
        self.service.groq_client = mock_client

        # Setup local success
        mock_local_transcribe.return_value = "Local Result"

        # Mock file IO
        m = mock_open(read_data=b"data")
        with patch("builtins.open", m):
            result = await self.service.transcribe_audio("test.ogg")

        self.assertEqual(result, "Local Result")

        # Verify local Whisper WAS called
        mock_local_transcribe.assert_called_once()
