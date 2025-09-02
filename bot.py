import os
import time
import threading
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Ympäristömuuttujat
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

if not BOT_TOKEN or not CHANNEL_ID:
    raise ValueError("BOT_TOKEN tai CHANNEL_ID ei ole määritelty ympäristömuuttujissa!")

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

# /commands komento
async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmds = [
        "/test",
        "/status",
        "/set_hours",
        "/set_top_percent"
    ]
    await update.message.reply_text("📄 Käytettävissä olevat komennot:\n" + "\n".join(cmds))

# ----- Taustasilmukka -----
def fetch_new_tokens():
    try:
        # Hae uusimmat tokenit SolScan API:sta
        url = "https://public-api.solscan.io/token/list?sortBy=createdBlock&direction=desc&limit=10"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print("Virhe uusien tokenien haussa:", r.text)
            return []
    except Exception as e:
        print("Virhe uusien tokenien haussa:", e)
        return []

def fetch_token_holders(token_address):
    try:
        url = f"https://public-api.solscan.io/account/tokens?tokenAddress={token_address}&limit=100"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            # Palautetaan holderien määrä
            return len(data.get("data", []))
        else:
            return 0
    except Exception as e:
        print("Virhe tokenin holderien haussa:", e)
        return 0

def signal_loop():
    while True:
        try:
            tokens = fetch_new_tokens()
            print("DEBUG: API-vastaus:", tokens)  # 👈 Näet lokista tuleeko mitään

            if not tokens:
                print("Ei uusia tokeneita tällä kierroksella.")
            else:
                token_info = []
                for t in tokens:
                    symbol = t.get("symbol", "N/A")
                    address = t.get("tokenAddress", "")
                    holders = fetch_token_holders(address)
                    token_info.append({"symbol": symbol, "address": address, "holders": holders})

                token_info.sort(key=lambda x: x["holders"], reverse=True)
                top_count = max(1, len(token_info) * top_percent // 100)
                top_tokens = token_info[:top_count]

                text = f"📊 Top {top_percent}% uusista tokeneista Solanassa:\n"
                for t in top_tokens:
                    text += f"- {t['symbol']} ({t['address']}), holders: {t['holders']}\n"
                app.bot.send_message(chat_id=CHANNEL_ID, text=text)
        except Exception as e:
            print("Virhe signal_loopissa:", e)

        time.sleep(hours_window * 3600)


def start_background_tasks():
    thread = threading.Thread(target=signal_loop, daemon=True)
    thread.start()

# ----- Webhookin poisto ennen pollingia -----
def remove_webhook(token):
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook"
        r = requests.post(url)
        if r.status_code == 200:
            print("Webhook poistettu onnistuneesti.")
        else:
            print("Webhookin poisto epäonnistui:", r.text)
    except Exception as e:
        print("Virhe webhookin poiston yhteydessä:", e)

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

    # Poista webhook, jotta ei tule conflict-virhettä
    remove_webhook(BOT_TOKEN)

    # Käynnistä botti (komennot)
    print("Botti käynnissä...")
    app.run_polling(drop_pending_updates=True)
