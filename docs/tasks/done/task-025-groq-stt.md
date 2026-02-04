# Feature: Groq STT Integration (Whisper Large V3)

**Status**: Done
**ID**: task-025

## Description
Integrate Groq's Audio API to use the **Whisper Large V3** model for speech-to-text (STT). This replaces the local Whisper Small model as the primary transcription engine, offering significantly higher accuracy (especially for Russian language, accents, and noisy environments) and ultra-low latency.

## Goals
1.  **Primary Engine**: Use Groq API (`whisper-large-v3`) for all voice message transcriptions.
2.  **Fallback Mechanism**: Keep the existing local `faster-whisper` (Small model) as a backup. If Groq API fails (e.g., network error, rate limit, blocking), the system automatically falls back to local processing.
3.  **Resource Optimization**: The local Whisper model is now loaded **lazily**. If Groq works 100% of the time, the local model is never loaded into RAM, saving ~1.5 GB of memory for other services (Sax).
4.  **Format Compatibility**: Implement automatic conversion of Telegram's OGG Opus voice messages to MP3 before sending to Groq to ensure API compatibility.

## Implementation Details
-   **Service**: Updated `TranslatorService` with `_transcribe_groq_sync`.
-   **Dependency**: Uses `pydub` for OGG->MP3 conversion (fast operation).
-   **Config**: Reuses `GROQ_API_KEY` and `HTTPS_PROXY` settings.
-   **Flow**:
    1.  User sends voice message.
    2.  Bot tries to transcribe via Groq (Large V3).
    3.  If successful -> returns text.
    4.  If error -> logs error -> loads/uses local Whisper (Small) -> returns text.

## Benefits
-   **Quality**: Massive improvement in recognition of mumbled speech, slang, and mixed languages.
-   **Performance**: Offloads heavy CPU inference to Groq's LPU cloud.
-   **Memory**: Potential to free up significant RAM on the host server.