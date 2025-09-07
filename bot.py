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
        url = "https://api.dexscreener.com/latest/dex/search?q=solana"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("pairs", [])
        else:
            error_msg = f"❌ Virhe uusien tokenien haussa (DexScreener): {r.text}"
            print(error_msg)
            try:
                app.bot.send_message(chat_id=CHANNEL_ID, text=error_msg)
            except Exception as e:
                print("⚠️ Ei voitu lähettää virheilmoitusta Telegramiin:", e)
            return []
    except Exception as e:
        error_msg = f"❌ Virhe uusien tokenien haussa: {e}"
        print(error_msg)
        try:
            app.bot.send_message(chat_id=CHANNEL_ID, text=error_msg)
        except Exception as e2:
            print("⚠️ Ei voitu lähettää virheilmoitusta Telegramiin:", e2)
        return []


def signal_loop():
    while True:
        try:
            tokens = fetch_new_tokens()
            if not tokens:
                msg = "⚠️ Ei uusia tokeneita tällä kierroksella."
                print(msg)
                try:
                    app.bot.send_message(chat_id=CHANNEL_ID, text=msg)
                except Exception as e:
                    print("⚠️ Ei voitu lähettää Telegramiin:", e)
            else:
                token_info = []
                for t in tokens:
                    base_token = t.get("baseToken", {})
                    symbol = base_token.get("symbol", "N/A")
                    address = base_token.get("address", "")
                    liquidity = t.get("liquidity", {}).get("usd", 0) or 0
                    volume24h = t.get("volume", {}).get("h24", 0) or 0

                    token_info.append({
                        "symbol": symbol,
                        "address": address,
                        "liquidity": liquidity,
                        "volume24h": volume24h
                    })

                token_info.sort(key=lambda x: x["volume24h"], reverse=True)
                top_count = max(1, len(token_info) * top_percent // 100)
                top_tokens = token_info[:top_count]

                text = f"📊 Top {top_percent}% Solana-tokeneista DexScreenerin mukaan:\n"
                for t in top_tokens:
                    text += (
                        f"- {t['symbol']} ({t['address']})\n"
                        f"   💧 Likviditeetti: ${t['liquidity']:.0f}\n"
                        f"   📈 24h volyymi: ${t['volume24h']:.0f}\n"
                    )

                try:
                    app.bot.send_message(chat_id=CHANNEL_ID, text=text)
                except Exception as e:
                    error_msg = f"❌ Virhe viestin lähetyksessä Telegramiin: {e}"
                    print(error_msg)
                    try:
                        app.bot.send_message(chat_id=CHANNEL_ID, text=error_msg)
                    except Exception as e2:
                        print("⚠️ Ei voitu lähettää virheilmoitusta Telegramiin:", e2)

        except Exception as e:
            error_msg = f"❌ Virhe signal_loopissa: {e}"
            print(error_msg)
            try:
                app.bot.send_message(chat_id=CHANNEL_ID, text=error_msg)
            except Exception as e2:
                print("⚠️ Ei voitu lähettää virheilmoitusta Telegramiin:", e2)

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
