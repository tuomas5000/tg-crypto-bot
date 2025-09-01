import os
from telegram import Bot

# Hakee bottitokenin Renderin ympäristömuuttujista
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # lisätään myöhemmin

bot = Bot(token=TOKEN)

if __name__ == "__main__":
    bot.send_message(chat_id=CHANNEL_ID, text="✅ Testisignaali: botti on käynnissä!")
