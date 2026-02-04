import io
import os
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from tg_translator.api import app, service

# Initialize Test Client
client = TestClient(app)


class TestRoyAPI:
    def setup_method(self):
        # Reset service mocks before each test
        # We use the REAL executor, but mock the methods it calls.
        # This allows loop.run_in_executor to work correctly with async tests.

        # Mock internal methods to avoid real API calls
        service._translate_sync = MagicMock()
        service.transcribe_audio = AsyncMock()
        service.generate_audio = AsyncMock()

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "tg-translator-ai"}

    def test_translate_success(self):
        """Test successful translation endpoint."""
        # Mock the run_in_executor call which wraps _translate_sync
        # Since we can't easily mock loop.run_in_executor in sync TestClient context without patching api.py logic,
        # we will patch the module level loop or the logic inside api.py.
        # However, api.py gets the running loop.

        # Easier approach: Patch the 'translate_text' endpoint's internal call logic?
        # No, integration test should test the endpoint.

        # The endpoint uses:
        # loop = asyncio.get_running_loop()
        # result = await loop.run_in_executor(...)

        # In TestClient (sync), there is no running loop for the request handler unless we use AsyncClient.
        # But FastAPI TestClient handles this magic.

        # We need to ensure that the mocked _translate_sync is called.
        # But run_in_executor runs it in a thread.

        # Let's mock the `service._translate_sync` to return a value.
        service._translate_sync.return_value = "Translated Text"

        # We also need to ensure the executor runs it. Standard TestClient usually handles async def endpoints correctly.

        response = client.post(
            "/translate",
            json={"text": "Hello", "source_lang": "en", "target_lang": "ru"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["translation"] == "Translated Text"
        assert data["source"] == "en"
        assert data["target"] == "ru"

    def test_translate_failure(self):
        """Test translation failure (empty result)."""
        service._translate_sync.return_value = None

        response = client.post(
            "/translate",
            json={"text": "Fail", "source_lang": "en", "target_lang": "ru"},
        )

        assert response.status_code == 500
        assert "Translation returned empty result" in response.json()["detail"]

    def test_stt_success(self):
        """Test STT endpoint with file upload."""
        service.transcribe_audio.return_value = "Speech Text"

        # Create dummy file
        file_content = b"fake audio data"
        files = {"file": ("test.ogg", file_content, "audio/ogg")}

        response = client.post("/stt", files=files)

        assert response.status_code == 200
        assert response.json()["text"] == "Speech Text"

        # Verify service call
        service.transcribe_audio.assert_called_once()
        # Check that temp file was created and passed
        call_args = service.transcribe_audio.call_args
        assert "tmp/roy_upload_" in call_args[0][0]

    def test_stt_failure(self):
        """Test STT failure."""
        service.transcribe_audio.return_value = None

        files = {"file": ("test.ogg", b"data", "audio/ogg")}
        response = client.post("/stt", files=files)

        assert response.status_code == 500
        assert "Transcription returned empty result" in response.json()["detail"]

    def test_tts_success(self):
        """Test TTS endpoint returns a file."""
        # Create a dummy mp3 file to return
        dummy_path = "tmp/test_tts.mp3"
        os.makedirs("tmp", exist_ok=True)
        with open(dummy_path, "wb") as f:
            f.write(b"mp3 data")

        service.generate_audio.return_value = dummy_path

        response = client.post(
            "/tts", json={"text": "Hello", "lang": "en", "gender": "male"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert response.content == b"mp3 data"

        # Cleanup
        if os.path.exists(dummy_path):
            os.remove(dummy_path)

    def test_tts_failure(self):
        """Test TTS failure."""
        service.generate_audio.return_value = None

        response = client.post("/tts", json={"text": "Hello", "lang": "en"})

        assert response.status_code == 500
        assert "TTS generation failed" in response.json()["detail"]
