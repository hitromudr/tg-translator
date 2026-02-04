from telegram import BotCommand

BOT_COMMANDS = [
    BotCommand("start", "Start bot / Запуск"),
    BotCommand("stop", "Stop bot / Стоп"),
    BotCommand("mute", "Interactive / Интерактив"),
    BotCommand("help", "Help / Справка"),
    BotCommand("dict", "Manage dictionary / Словарь"),
    BotCommand("lang", "Settings / Языки"),
    BotCommand("voice", "Voice gender / Голос"),
    BotCommand("clean", "Cleanup / Уборка"),
]
