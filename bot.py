import os
import asyncio
from telegram import Bot

# Telegram-token ja kanava
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

bot = Bot(token=TOKEN)

async def send_test_message():
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text="✅ Testisignaali: botti on käynnissä!")
        print("Testiviesti lähetetty onnistuneesti.")
    except Exception as e:
        print(f"Virhe viestin lähetyksessä: {e}")

# Vanha logiikka (jos halutaan myöhemmin lisätä)
async def vanha_logiikka():
    pass  # vanhat funktiot

if __name__ == "__main__":
    asyncio.run(vanha_logiikka())
    asyncio.run(send_test_message())
