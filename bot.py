import os
import asyncio
import requests
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, timedelta

# --- Telegram ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")
HEADERS = {"token": SOLSCAN_API_KEY}
bot = Bot(token=TOKEN)

# --- Parametrit ---
hours = 1
top_percent = 5

SOLSCAN_NEW_TOKENS = "https://public-api.solscan.io/v1/token/new"
SOLSCAN_TOKEN_TXS = "https://public-api.solscan.io/v1/token/txs"

# --- Telegram-komennot ---
async def set_hours(update: ContextTypes.DEFAULT_TYPE, context: ContextTypes.DEFAULT_TYPE):
    global hours
    if context.args:
        hours = int(context.args[0])
        await update.message.reply_text(f"✅ Aikaväli asetettu {hours} tunniksi")
    else:
        await update.message.reply_text("Käyttö: /set_hours <tunnit>")

async def set_top_percent(update: ContextTypes.DEFAULT_TYPE, context: ContextTypes.DEFAULT_TYPE):
    global top_percent
    if context.args:
        top_percent = int(context.args[0])
        await update.message.reply_text(f"✅ Top-prosentti asetettu {top_percent}%")
    else:
        await update.message.reply_text("Käyttö: /set_top_percent <prosentti>")

async def status(update: ContextTypes.DEFAULT_TYPE, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🛠 Nykyiset parametrit:\nAikaväli: {hours}h\nTop-prosentti: {top_percent}%")

async def send_test_message(update: ContextTypes.DEFAULT_TYPE, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Testiviesti: botti toimii ja Telegram-yhteys OK!")

# --- Solscan ---
def fetch_new_tokens():
    tokens = []
    try:
        response = requests.get(SOLSCAN_NEW_TOKENS, headers=HEADERS, timeout=10)
        data = response.json()
        for token in data.get("data", []):
            if token.get("market_cap_usd", 1_000_001) < 10_000_000:
                tokens.append({
                    "name": token["tokenName"],
                    "symbol": token["symbol"],
                    "market_cap": token.get("market_cap_usd", "n/a"),
                    "address": token["tokenAddress"]
                })
    except Exception as e:
        print(f"Virhe uusien tokenien haussa: {e}")
    return tokens

def count_buyers(token_address, hours_param):
    try:
        params = {"token": token_address, "limit": 100}
        response = requests.get(SOLSCAN_TOKEN_TXS, headers=HEADERS, params=params, timeout=10)
        data = response.json().get("data", [])
        unique_buyers = set()
        cutoff = datetime.utcnow() - timedelta(hours=hours_param)
        for tx in data:
            ts = datetime.utcfromtimestamp(tx["blockTime"])
            if ts > cutoff and tx["amount"] > 0:
                unique_buyers.add(tx["from"])
        return len(unique_buyers)
    except Exception as e:
        print(f"Virhe ostajien laskennassa: {e}")
        return 0

async def send_signal_message():
    tokens = fetch_new_tokens()
    buyer_counts = []

    for token in tokens:
        buyers = count_buyers(token["address"], hours)
        token["buyers"] = buyers
        buyer_counts.append(buyers)

    if not buyer_counts:
        print("Ei ostotietoja tällä kierroksella.")
        return

    threshold_index = max(0, int(len(buyer_counts)*(top_percent/100))-1)
    threshold = max(1, sorted(buyer_counts, reverse=True)[threshold_index])

    for token in tokens:
        if token["buyers"] >= threshold:
            msg = (f"🚀 Top token: {token['name']} ({token['symbol']})\n"
                   f"Market cap: {token['market_cap']}\n"
                   f"Ostajia viime {hours}h aikana: {token['buyers']}\n"
                   f"Address: {token['address']}")
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=msg)
                print(f"Lähetetty top token: {token['name']}")
            except Exception as e:
                print(f"Virhe viestin lähetyksessä: {e}")

async def signal_loop():
    while True:
        await send_signal_message()
        await asyncio.sleep(3600)  # 1h välein

# --- Main ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Telegram-komennot
    app.add_handler(CommandHandler("set_hours", set_hours))
    app.add_handler(CommandHandler("set_top_percent", set_top_percent))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("test", send_test_message))

    # Käynnistä taustasilmukka suoraan nykyisessä loopissa
    loop = asyncio.get_event_loop()
    loop.create_task(signal_loop())

    # Käynnistä Telegram polling synkronisesti
    app.run_polling()
