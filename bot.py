import os
import time
import threading
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Ympäristömuuttujat
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

if not BOT_TOKEN or CHANNEL_ID == 0:
    raise ValueError("BOT_TOKEN tai CHANNEL_ID ei ole määritelty ympäristömuuttujissa!")

# Parametrit
hours_window = 1.0   # oletus 1h
top_percent = 5

# Telegram-botin alustus
app = Application.builder().token(BOT_TOKEN).build()

# ----- Dexscreener API -----
def fetch_new_tokens():
    try:
        url = "https://api.dexscreener.com/latest/dex/tokens"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("pairs", [])
        else:
            print("Virhe API-haussa:", r.text)
            return []
    except Exception as e:
        print("Virhe API-haussa:", e)
        return []

# ----- Taustasilmukka -----
def signal_loop():
    while True:
        try:
            tokens = fetch_new_tokens()
            if not tokens:
                print("Ei uusia tokeneita tällä kierroksella.")
            else:
                # Järjestetään volume24h mukaan
                tokens.sort(key=lambda x: float(x.get("volume", {}).get("h24", 0)), reverse=True)
                top_count = max(1, len(tokens) * top_percent // 100)
                top_tokens = tokens[:top_count]

                # Viesti Telegramiin
                text = f"📊 Top {top_percent}% tokeneista Dexscreeneristä:\n"
                for t in top_tokens:
                    symbol = t.get("baseToken", {}).get("symbol", "N/A")
                    address = t.get("baseToken", {}).get("address", "")
                    volume = t.get("volume", {}).get("h24", 0)
                    text += f"- {symbol} ({address}), 24h vol: {volume}\n"

                app.bot.send_message(chat_id=CHANNEL_ID, text=text)
        except Exception as e:
            print("Virhe signal_loopissa:", e)

        time.sleep(hours_window * 3600)

def start_background_tasks():
    thread = threading.Thread(target=signal_loop, daemon=True)
    thread.start()

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
        value = float(context.args[0])
        if 0.1 <= value <= 24:
            hours_window = value
            await update.message.reply_text(f"✅ Aikaväli asetettu: {hours_window}h")
        else:
            await update.message.reply_text("⚠️ Anna arvo väliltä 0.1–24 tuntia.")
    except Exception:
        await update.message.reply_text("⚠️ Käyttö: /set_hours <tunnit> (0.1–24)")

async def set_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global top_percent
    try:
        value = int(context.args[0])
        if 1 <= value <= 100:
            top_percent = value
            await update.message.reply_text(f"✅ Top % asetettu: {top_percent}")
        else:
            await update.message.reply_text("⚠️ Anna arvo väliltä 1–100.")
    except Exception:
        await update.message.reply_text("⚠️ Käyttö: /set_top_percent <prosentti>")

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 Komennot:\n"
        "/test – Testaa botti\n"
        "/status – Näytä nykyiset asetukset\n"
        "/set_hours <0.1–24> – Aseta viestien aikaväli (tunneissa)\n"
        "/set_top_percent <1–100> – Aseta top % filtteri\n"
        "/commands – Näytä tämä lista"
    )

# ----- Main -----
if __name__ == "__main__":
    # Lisää komennot
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("set_hours", set_hours_command))
    app.add_handler(CommandHandler("set_top_percent", set_top_command))
    app.add_handler(CommandHandler("commands", commands_command))

    # Käynnistä taustasäie
    start_background_tasks()

    # Käynnistä botti
    print("Botti käynnissä...")
    app.run_polling()
