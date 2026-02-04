# Improvement: Upgrade Whisper Model to 'Small'

**Status**: In Progress
**ID**: task-016

## Description
The initial integration of Whisper used the `base` model to minimize resource usage. However, user testing revealed that the `base` model struggles with unclear speech or rapid "mumbling" in Russian, producing hallucinations or nonsensical transcriptions.
Since the server has ample resources (4 vCPUs, 8GB RAM, with ~6GB free), we can safely upgrade to the `small` model to significantly improve accuracy without compromising the stability of co-hosted services (SAX).

## Goals
1.  **Code Change**:
    -   Update `TranslatorService._get_whisper_model` to load `model_size="small"` instead of `"base"`.
2.  **Verify Resources**:
    -   Ensure `cpu_threads=2` limit remains to protect LiveKit performance.
    -   The `small` model requires approx. 500MB RAM (vs 150MB for `base`), which is well within limits.

## Technical Details
-   **Model**: `small` (approx 461M parameters).
-   **Compute Type**: `int8` (to keep inference fast on CPU).
-   **Latency**: Inference time will increase slightly (approx 2x slower than base), but correctness is prioritized over sub-second latency for this use case.

## Benefits
-   **Accuracy**: Much better handling of accents, fast speech, and background noise.
-   **Quality**: Fewer hallucinations (inventing words that weren't said).