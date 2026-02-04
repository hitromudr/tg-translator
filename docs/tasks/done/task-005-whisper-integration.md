# Feature: Integrate Self-Hosted Whisper for Voice Recognition

**Status**: In Progress
**ID**: task-005

## Description
The current voice recognition implementation relies on the legacy `SpeechRecognition` library and Google's free Speech API. To provide a modern "Wow" experience, we will migrate to **Whisper** running locally on the server.
Server analysis confirmed 4 vCPUs and 8GB RAM are available. The server also hosts "SAX" (a LiveKit-based video app), so we must limit Whisper's resource usage to avoid CPU starvation during video calls.

## Goals
1.  **Dependencies**:
    -   Add `faster-whisper` to `pyproject.toml` (and remove `SpeechRecognition` if fully replaced).
    -   Ensure `ffmpeg` is installed on the server (Ansible playbook already includes it).

2.  **Implementation**:
    -   Update `TranslatorService` to use `faster-whisper`.
    -   Use the `base` model (good balance of speed/quality).
    -   Implement **Lazy Loading**: Load the model only on the first voice message to keep startup fast.
    -   **Resource Safety**: Set `cpu_threads=2` to ensure 2 cores remain free for LiveKit/SAX.

3.  **Refactor**:
    -   Rewrite `transcribe_audio` method.
    -   Whisper accepts OGG/MP3 directly, so `pydub` (OGG->WAV) conversion might be redundant.

4.  **Testing**:
    -   Update unit tests to mock the heavy Whisper model.

## Benefits
-   **Accuracy**: Near-human level recognition accuracy.
-   **Cost**: $0 (running on existing hardware).
-   **Privacy**: Audio never leaves the server.
-   **Stability**: No dependence on external API rate limits or network blocks.

## Technical Details
-   **Model**: `base` (approx 140MB RAM + runtime overhead).
-   **Compute**: `int8` quantization for speed on CPU.
-   **Concurrency**: `cpu_threads=2` (Server has 4 cores).