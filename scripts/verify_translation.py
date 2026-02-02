import asyncio
import os
import sys

# Ensure src is in python path so we can import the module
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from tg_translator.translator_service import TranslatorService


async def main():
    print("Initializing Translator Service...")
    service = TranslatorService()

    # Omar Khayyam in Russian
    ru_text = (
        "Чтоб мудро жизнь прожить, знать надобно немало,\n"
        "Два важных правила запомни для начала:\n"
        "Ты лучше голодай, чем что попало есть,\n"
        "И лучше будь один, чем вместе с кем попало."
    )

    # Omar Khayyam in English
    en_text = (
        "The Moving Finger writes; and, having writ,\n"
        "Moves on: nor all your Piety nor Wit\n"
        "Shall lure it back to cancel half a Line,\n"
        "Nor all your Tears wash out a Word of it."
    )

    print("-" * 60)
    print("TEST 1: Russian -> English")
    print("-" * 60)
    print(f"ORIGINAL:\n{ru_text}\n")
    translation_en = await service.translate_message(ru_text)
    print(f"TRANSLATION:\n{translation_en}\n")

    print("-" * 60)
    print("TEST 2: English -> Russian")
    print("-" * 60)
    print(f"ORIGINAL:\n{en_text}\n")
    translation_ru = await service.translate_message(en_text)
    print(f"TRANSLATION:\n{translation_ru}\n")

    service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
