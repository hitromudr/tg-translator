# Telegram Translator Bot

A Telegram bot that automatically translates messages in group chats. It detects the language of the message and translates it:
- Cyrillic text (Russian, etc.) -> English
- Other text (English, Latin, etc.) -> Russian

## Features

- **Automatic Language Detection**: Uses a simple heuristic (presence of Cyrillic characters) to determine the translation direction.
- **Privacy First**: Only translates text messages, ignores commands and other media unless configured otherwise.
- **Easy Deployment**: Docker-ready (planned) and Ansible playbook included.

## Requirements

- Python 3.10+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd tg-translator
   ```

2. **Set up the environment:**
   Create a `.env` file in the root directory and add your bot token:
   ```bash
   cp config_example.txt .env
   # Edit .env and set TELEGRAM_BOT_TOKEN
   ```

3. **Install dependencies:**
   Using `make`:
   ```bash
   make install
   ```
   Or manually:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

## Usage

1. **Run the bot:**
   ```bash
   make run
   ```

2. **Add the bot to a group:**
   Add the bot to your Telegram group. Ensure it has access to messages (you might need to disable "Group Privacy" in BotFather settings if you want it to see all messages, or just mention it/reply to it depending on setup. *Note: Current implementation listens to all text messages, so Privacy Mode must be disabled in BotFather for the bot to see messages in groups without being an admin or explicitly mentioned.*)

3. **Send a message:**
   - Type in Russian -> Bot replies with English translation.
   - Type in English -> Bot replies with Russian translation.

## Development

### Running Tests

```bash
make test
```

### Code Formatting and Linting

```bash
make format
make lint
```

## Deployment

The project includes an Ansible playbook for deployment.

1. Update `deploy/inventory` with your server details.
2. Run:
   ```bash
   make deploy
   ```

## License

MIT