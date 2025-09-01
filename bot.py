import os
from telegram import Bot
from time import sleep

# --- Telegram-token ja kanava ID Renderin ympäristömuuttujista ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

bot = Bot(token=TOKEN)

# --- Funktio testiviestin lähettämiseen ---
def send_test_message():
    try:
        bot.send_message(chat_id=CHANNEL_ID, text="✅ Testisignaali: botti on käynnissä!")
        print("Testiviesti lähetetty onnistuneesti.")
    except Exception as e:
        print(f"Virhe viestin lähetyksessä: {e}")

# --- Mahdollinen vanha logiikka funktioina ---
def vanha_logiikka():
    # Lisää tähän vanha koodisi funktiot
    pass

# --- Main-lohko ---
if __name__ == "__main__":
    vanha_logiikka()     # vanha koodi
    send_test_message()  # uusi testiviesti
