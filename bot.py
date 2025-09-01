import os
import asyncio
from telegram import Bot

# --- Telegram-token ja kanava ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

bot = Bot(token=TOKEN)

# --- Funktio viestin lähettämiseen ---
async def send_signal_message():
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text="📢 Kryptosignaali: testiviesti!")
        print("Viestilähetys onnistui.")
    except Exception as e:
        print(f"Virhe viestin lähetyksessä: {e}")

# --- Taustasilmukka, joka lähettää viestin 1 tunnin välein ---
async def signal_loop():
    while True:
        await send_signal_message()
        await asyncio.sleep(3600)  # 3600 sekuntia = 1 tunti

# --- Pääohjelma ---
if __name__ == "__main__":
    asyncio.run(signal_loop())
