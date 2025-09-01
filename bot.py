import os
import time
import threading
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Ympäristömuuttujat
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if BOT_TOKEN is None or CHANNEL_ID is None:
    raise ValueError("BOT_TOKEN tai CHANNEL_ID ei ole määritelty ympäristömuuttujissa!")

CHANNEL_ID = int(CHANNEL_ID)

# Parametrit
hours_window = 1
top_percent = 5

# Telegram-botin alustus
app = Application.builder().token(BOT_TOKEN).build()

# ----- Komennot -----
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Testiviesti: botti vastaa komentoihin.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"ℹ️ Parametrit nyt:\nAikaväli: {hours_window}h\nTop %: {top_percent}"
    )

async def set_hours_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global hours_window
    try:
        value = int(context.args[0])
        hours_window = value
        await update.message.reply_text(f"✅ Aikaväli asetettu: {hours_window}h")
    except Exception:
        await update.message.reply_text("⚠️ Käyttö: /set_hours <tunnit>")

async def set_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global top_percent
    try:
        value = int(context.args[0])
        top_percent = value
        await update.message.reply_text(f"✅ Top % asetettu: {top_percent}")
    except Exception:
        await update.message.reply_text("⚠️ Käyttö: /set_top_percent <prosentti>")

# Lisätty /commands-komento
async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands_list = "/test\n/status\n/set_hours\n/set_top_percent"
    await update.message.reply_text(f"📋 Saatavilla olevat komennot:\n{commands_list}")

# ----- Taustasilmukka -----
def fetch_new_tokens():
    try:
        url = "https://public-api.solscan.io/token/list?sortBy=createdBlock&direction=desc&limit=5"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print("Virhe uusien tokenien haussa:", r.text)
            return []
    except Exception as e:
        print("Virhe uusien tokenien haussa:", e)
        return []

def signal_loop():
    while True:
        try:
            tokens = fetch_new_tokens()
            if not tokens:
                print("Ei uusia tokeneita tällä kierroksella.")
            else:
                text = "📊 Uudet tokenit Solanassa:\n"
                for t in tokens:
                    text += f"- {t.get('symbol', 'N/A')} ({t.get('tokenAddress', '')})\n"
                app.bot.send_message(chat_id=CHANNEL_ID, text=text)
        except Exception as e:
            print("Virhe signal_loopissa:", e)

        time.sleep(hours_window * 3600)

def start_background_tasks():
    thread = threading.Thread(target=signal_loop, daemon=True)
    thread.start()

# ----- Main -----
if __name__ == "__main__":
    # Lisää komennot
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("set_hours", set_hours_command))
    app.add_handler(CommandHandler("set_top_percent", set_top_command))
    app.add_handler(CommandHandler("commands", commands_command))  # <- uusi

    # Käynnistä taustasäie
    start_background_tasks()

    # Käynnistä botti (komennot)
    print("Botti käynnissä...")
    app.run_polling()
