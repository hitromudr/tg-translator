# Feature: Context-Aware LLM Translation

**Status**: Done
**ID**: task-007

## Description
Standard translation APIs (like Google Translate) often miss context, idioms, or tone, resulting in literal translations that can sound robotic. By integrating Large Language Models (LLMs) like OpenAI's GPT-4o-mini or Google Gemini, we can offer "Smart Translation" that understands nuance, style, and intent.

## Goals
1.  **Select Provider**: Selected **Groq** (running Llama 3.3 70B) for ultra-low latency.
2.  **API Integration**:
    -   Integrated `groq` python client into `TranslatorService`.
    -   Implemented automatic fallback: Groq -> Google Translate.
    -   Designed system prompts for high-quality, context-aware translation.
3.  **Configuration**:
    -   Added support for `GROQ_API_KEY` (and `GROK_API_KEY`).
    -   Ensured Proxy support via `HTTPS_PROXY` for operation in restricted regions.
4.  **Error Handling**: Graceful fallback ensures reliability even if the LLM API is down or blocked.

## Benefits
-   **Quality**: Significantly better handling of slang, idioms, and ambiguous sentences.
-   **Customization**: Ability to support different translation styles (e.g., "Translate this for a business email" vs "Translate this for a friend").
-   **Correction**: LLMs can implicitly correct typos in the source text before translating, leading to better results.

## Technical Details
-   Requires `GROQ_API_KEY`.
-   **Latency**: Groq inference is extremely fast, comparable to standard APIs.
-   **Network**: Requires `HTTPS_PROXY` if server IP is blocked by US providers.