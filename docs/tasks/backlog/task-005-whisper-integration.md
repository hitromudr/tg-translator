# Feature: Integrate OpenAI Whisper for Voice Recognition

**Status**: Backlog
**ID**: task-005

## Description
The current voice recognition implementation relies on the legacy `SpeechRecognition` library and Google's free Speech API. This solution often fails with background noise, accents, or mixed languages. To provide a modern "Wow" experience, we should migrate to OpenAI's **Whisper** model.

## Goals
1.  **Analyze Implementation Strategy**:
    -   Option A: **OpenAI API** (`whisper-1`). Pros: Highest quality, no server load, easy implementation. Cons: Costs money (though very cheap).
    -   Option B: **Local Inference** (e.g., `faster-whisper`). Pros: Free, privacy. Cons: High CPU/RAM usage, requires `ffmpeg` and potentially GPU for speed.
    -   *Recommendation*: Start with Option A (API) for immediate quality boost with minimal infrastructure impact.
2.  Add `openai` library to dependencies (`pyproject.toml` or `requirements.txt`).
3.  Add `OPENAI_API_KEY` to environment variables and `.env`.
4.  Refactor `TranslatorService.transcribe_audio` to use the Whisper client.
5.  (Optional) Remove `SpeechRecognition` dependency if no longer needed as fallback.

## Benefits
-   **Accuracy**: Near-human level recognition accuracy.
-   **Language Support**: Whisper automatically detects languages and handles code-switching much better than legacy tools.
-   **User Experience**: Users can speak naturally without "robot voice" enunciation.

## Technical Details
-   Current `transcribe_audio` logic converts OGG to WAV. Whisper API accepts OGG/MP3 directly, which might simplify the pipeline (removing `pydub` conversion step).
-   Limit audio file size to 25MB (Whisper API limit), though Telegram voice messages are rarely that large.