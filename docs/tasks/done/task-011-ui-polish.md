# Feature: UI Polish - Minimalist Interactive Mode

**Status**: In Progress
**ID**: task-011

## Description
In interactive mode, the bot sends single emojis (`🎤` or `🌐`) as placeholders. Telegram automatically renders single emojis as large "stickers," which takes up unnecessary space. The user also requested changing the text placeholder icon to a memo/pencil style.

## Goals
1.  **Icon Change**:
    -   Replace the Globe `🌐` with a Memo/Pencil `📝` for text translation placeholders.

2.  **Prevent Upscaling**:
    -   Append a "Zero Width Space" (`\u200b`) or similar invisible character to the emoji. This forces Telegram to render it as a standard text bubble (tiny) instead of a large sticker.

3.  **Update Logic**:
    -   Update `handlers/translation.py` to send `📝\u200b` and `🎤\u200b`.
    -   Update `handlers/callback_translate.py` to correctly identify and strip these new placeholders when processing the button click.

## Benefits
-   **Compactness**: The bot's reply will occupy the absolute minimum screen real estate possible while maintaining the "reply" link context.
-   **Aesthetics**: The memo icon better represents "text to be translated/edited".