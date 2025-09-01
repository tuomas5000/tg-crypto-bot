import os
import asyncio
import requests
from telegram import Bot

# --- Telegram ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
bot = Bot(token=TOKEN)

# --- Solscan API ---
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")
HEADERS = {"token": SOLSCAN_API_KEY}
SOLSCAN_URL = "https://public-api.solscan.io/v1/token/new"

# --- Hae lupaavat tokenit ---
def fetch_promising_tokens():
    promising = []
    try:
        response = requests.get(SOLSCAN_URL, headers=HEADERS)
        data = response.json()

        for token in data.get("data", []):
            # Filter: alle 10M market cap
            if token.get("market_cap_usd", 1_000_001) < 10_000_000:
                promising.append({
                    "name": token["tokenName"],
                    "symbol": token["symbol"],
                    "market_cap": token.get("market_cap_usd", "n/a"),
                    "address": token["tokenAddress"]
                })
    except Exception as e:
        print(f"Virhe tokenien haussa: {e}")
    return promising

# --- Lähetä Telegramiin ---
async def send_signal_message():
    tokens = fetch_promising_tokens()
    if not tokens:
        print("Ei lupaavia tokeneita tällä kierroksella.")
        return

    for token in tokens:
        msg = f"🚀 Lupaava token: {token['name']} ({token['symbol']})\nMarket cap: {token['market_cap']}\nAddress: {token['address']}"
        try:
            await bot.send_message(chat_id=CHANNEL_ID, text=msg)
            print(f"Lähetetty signaali: {token['name']}")
        except Exception as e:
            print(f"Virhe viestin lähetyksessä: {e}")

# --- Taustasilmukka 1h välein ---
async def signal_loop():
    while True:
        await send_signal_message()
        await asyncio.sleep(3600)  # 1 tunti

if __name__ == "__main__":
    asyncio.run(signal_loop())
