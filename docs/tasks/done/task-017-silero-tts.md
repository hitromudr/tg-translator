# Feature: High-Quality Neural TTS (Silero)

**Status**: In Progress
**ID**: task-017

## Description
The current Text-to-Speech solution (`gTTS`) produces robotic, unnatural audio. The user specifically noted poor quality for Ukrainian. We will integrate **Silero TTS**, a lightweight and high-quality neural TTS engine that runs efficiently on CPUs.

## Goals
1.  **Dependencies**:
    -   Add `torch` and `torchaudio` (CPU versions preferred to save disk space) to `pyproject.toml`.
    -   Add `omegaconf` (usually required by Silero).

2.  **Implementation**:
    -   Extend `TranslatorService` with a new method `_generate_audio_silero`.
    -   Implement a language router:
        -   **Primary (Silero)**: `ru`, `en`, `uk` (Ukrainian), `de`, `es`, `fr`.
        -   **Fallback (gTTS)**: All other languages (e.g., Chinese, Japanese).
    -   **Speaker Selection**: Choose standard pleasant voices (e.g., `kseniya` for RU, `en_0` for EN, `mykyta` for UK).

3.  **Resource Management**:
    -   Implement **Lazy Loading**: Load the Silero model into RAM only when a TTS request for that language comes in.
    -   Cache loaded models in `self.tts_models` dictionary to avoid reloading on every request (we have enough RAM to keep a few active).

## Technical Details
-   **Library**: Use `torch.hub.load(repo_or_dir='snakers4/silero-models', ...)` for easy model management.
-   **Models**: Use v4 models where available for best quality.
-   **Output**: Silero generates raw audio (tensor). Need to convert it to a file format Telegram accepts (OGG/MP3) using `torchaudio` or `scipy.io.wavfile` + `ffmpeg`.

## Benefits
-   **Quality**: Near-human intonation and prosody.
-   **Speed**: Runs faster than real-time on the server's Xeon CPU.
-   **Efficiency**: Self-hosted, no external API latency or costs.