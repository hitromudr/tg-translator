# TG Translator Bot 🤖

A powerful, self-hosted Telegram bot for seamless multilingual communication in group chats. Designed for privacy, speed, and high-quality voice interactions.

![Status](https://img.shields.io/badge/Status-Active-green)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![STT](https://img.shields.io/badge/STT-Whisper-orange)
![TTS](https://img.shields.io/badge/TTS-Silero-purple)

## 🚀 Features

### 💬 Translation
*   **Automatic Translation**: Instantly translates text messages between configured languages (default: RU ↔ EN).
*   **Smart Dictionary**: Supports custom term replacements (e.g., specific names or slang) with automatic case handling.
*   **Auto-Detection**: Intelligently detects source language, even when mixed with dictionary substitutions.

### 🎙 Voice (Speech-to-Text)
*   **Whisper AI**: Uses OpenAI's **Whisper (Small)** model running locally for high-accuracy recognition of accents, fast speech, and mixed languages.
*   **Privacy-First**: Audio is processed on your server, never sent to third-party clouds.

### 🔊 Voice (Text-to-Speech)
*   **Silero TTS**: High-quality neural speech synthesis for **Russian, English, Ukrainian, German, Spanish, French**.
*   **Voice Control**:
    *   Switch between **Male** and **Female** voices globally (`/voice male/female`).
    *   Set specific speakers for specific languages (`/voice set`).
    *   Test voices before using (`/voice test`).
*   **Fallback**: Automatically degrades to Google TTS for unsupported languages.

### ⚙️ Modes & UX
*   **Auto Mode** (`/start`): Translates everything immediately.
*   **Interactive Mode** (`/mute`): Silent. Shows a minimal button (`📝` / `🎤`) to translate on demand.
*   **Off Mode** (`/stop`): Bot is completely disabled until reactivated.
*   **Smart Clean**: `/clean` command intelligently removes bot clutter without deleting user messages.

---

## 🛠 Commands

### General
*   `/start` - Enable **Auto Mode** (Translates all messages).
*   `/stop` - Enable **Off Mode** (Bot ignores everything).
*   `/mute` - Enable **Interactive Mode** (Reply with "Translate" button).
*   `/help` - Show help message.

### Settings
*   `/lang set <L1> <L2>` - Set language pair (e.g., `/lang set ru en`).
*   `/lang status` - Show current languages.
*   `/clean [N]` - Delete last N bot messages (smart scan).

### Voice Control
*   `/voice male` / `/voice female` - Set global gender preference.
*   `/voice list [lang]` - List available speakers for a language.
*   `/voice test <lang> <speaker>` - Generate a test sample.
*   `/voice set <lang> <gender> <speaker>` - Assign a specific speaker to a language/gender.
*   `/voice reset` - Clear custom presets.

### Dictionary
*   `/dict add <word> <translation>` - Add a custom term.
*   `/dict remove <word>` - Remove a term.
*   `/dict list` - List all terms.
*   `/dict export` / `/dict import` - Backup/Restore dictionary.

---

## 🏗 Architecture

The bot is designed to run on a standard VPS (e.g., 4 vCPU, 8GB RAM).

*   **Core**: Python 3.10+, `python-telegram-bot`.
*   **Database**: SQLite (with automatic migrations).
*   **STT Engine**: `faster-whisper` (optimized for CPU).
*   **TTS Engine**: `silero-tts` (via `torch` + `soundfile`).
*   **Translation**: Google Translate (via `deep-translator`).

### Performance Limits
*   **Whisper**: Configured to use `int8` quantization and limited to 2 CPU threads to coexist safely with other high-load services (like LiveKit).
*   **Silero**: Lazy-loaded into RAM only when needed.

---

## 📦 Deployment

### Prerequisites
*   Python 3.10+
*   ffmpeg (installed on system)
*   git

### Installation (Local/VPS)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/hitromudr/tg-translator.git
    cd tg-translator
    ```

2.  **Create `.env` file:**
    ```bash
    cp .env.example .env
    # Edit .env and add your TELEGRAM_BOT_TOKEN
    ```

3.  **Install dependencies:**
    ```bash
    make install
    # or for dev: make dev-install
    ```

4.  **Run:**
    ```bash
    make run
    ```

### Docker (Planned)
Docker support is in the backlog. Currently deployed via Ansible/Makefile.

---

## 📝 License
MIT