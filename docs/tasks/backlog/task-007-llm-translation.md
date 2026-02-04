# Feature: Context-Aware LLM Translation

**Status**: Backlog
**ID**: task-007

## Description
Standard translation APIs (like Google Translate) often miss context, idioms, or tone, resulting in literal translations that can sound robotic. By integrating Large Language Models (LLMs) like OpenAI's GPT-4o-mini or Google Gemini, we can offer "Smart Translation" that understands nuance, style, and intent.

## Goals
1.  **Select Provider**: Evaluate OpenAI (GPT-4o-mini) vs Google Gemini API based on cost/latency.
2.  **API Integration**:
    -   Create a new translator backend/adapter in `TranslatorService` for the LLM.
    -   Design system prompts for translation (e.g., "You are a professional translator. Translate the following text from {source} to {target}, preserving the informal tone...").
3.  **User Interface**:
    -   Add a toggle or specific command (e.g., `/smart_mode` or a settings switch) to enable LLM-based translation.
    -   Consider implementing a "Style" selector (Formal, Casual, etc.).
4.  **Error Handling**: Ensure graceful fallback to the standard translation engine if the LLM API is unavailable or times out.

## Benefits
-   **Quality**: Significantly better handling of slang, idioms, and ambiguous sentences.
-   **Customization**: Ability to support different translation styles (e.g., "Translate this for a business email" vs "Translate this for a friend").
-   **Correction**: LLMs can implicitly correct typos in the source text before translating, leading to better results.

## Technical Details
-   Requires `OPENAI_API_KEY` or `GOOGLE_API_KEY`.
-   **Latency**: LLMs are slower than standard translation APIs. We must ensure the bot sends a "typing" action or a "Thinking..." status message to keep the user engaged.
-   **Cost**: Monitoring token usage is essential to prevent unexpected costs.