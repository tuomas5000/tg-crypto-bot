import os
import asyncio
import requests
from telegram import Bot
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")
HEADERS = {"token": SOLSCAN_API_KEY}

bot = Bot(token=TOKEN)
SOLSCAN_NEW_TOKENS = "https://public-api.solscan.io/v1/token/new"
SOLSCAN_TOKEN_TXS = "https://public-api.solscan.io/v1/token/txs"

# --- Hae uudet tokenit ---
def fetch_new_tokens():
    tokens = []
    try:
        response = requests.get(SOLSCAN_NEW_TOKENS, headers=HEADERS)
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

# --- Laske ostajamäärä tietyn aikavälin sisällä ---
def count_buyers(token_address, hours=1):
    try:
        params = {"token": token_address, "limit": 100}
        response = requests.get(SOLSCAN_TOKEN_TXS, headers=HEADERS, params=params)
        data = response.json().get("data", [])
        unique_buyers = set()
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        for tx in data:
            ts = datetime.utcfromtimestamp(tx["blockTime"])
            if ts > cutoff and tx["amount"] > 0:  # ostotapahtumat
                unique_buyers.add(tx["from"])
        return len(unique_buyers)
    except Exception as e:
        print(f"Virhe ostajien laskennassa: {e}")
        return 0

# --- Lähetä top 1% tokenit Telegramiin ---
async def send_signal_message():
    tokens = fetch_new_tokens()
    buyer_counts = []

    # Laske ostajamäärät
    for token in tokens:
        buyers = count_buyers(token["address"], hours=1)
        token["buyers"] = buyers
        buyer_counts.append(buyers)

    if not buyer_counts:
        print("Ei ostotietoja tällä kierroksella.")
        return

    # Laske top 1%
    threshold = max(1, int(sorted(buyer_counts, reverse=True)[max(1, int(len(buyer_counts)*0.01))-1]))

    for token in tokens:
        if token["buyers"] >= threshold:
            msg = (f"🚀 Top token: {token['name']} ({token['symbol']})\n"
                   f"Market cap: {token['market_cap']}\n"
                   f"Ostajia viime tunnin aikana: {token['buyers']}\n"
                   f"Address: {token['address']}")
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=msg)
                print(f"Lähetetty top token: {token['name']}")
            except Exception as e:
                print(f"Virhe viestin lähetyksessä: {e}")

# --- Taustasilmukka 1h välein ---
async def signal_loop():
    while True:
        await send_signal_message()
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(signal_loop())
