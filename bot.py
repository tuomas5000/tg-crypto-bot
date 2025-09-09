# bot.py
import os
import asyncio
import logging
from aiohttp import web
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from flask import Flask, request

APP_URL = os.getenv("APP_URL")  # esim. https://sunbotinurl.onrender.com

app = Flask(__name__)

# --- Konfiguraatio (ympäristömuuttujat) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID_ENV = os.environ.get("CHANNEL_ID")
APP_URL = os.environ.get("APP_URL")  # esim. https://my-app.onrender.com
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")  # oletus /webhook
PORT = int(os.environ.get("PORT", "8080"))

if not BOT_TOKEN or not CHANNEL_ID_ENV or not APP_URL:
    raise SystemExit("VIRHE: Aseta ympäristömuuttujat BOT_TOKEN, CHANNEL_ID ja APP_URL ennen käynnistystä.")

try:
    CHANNEL_ID = int(CHANNEL_ID_ENV)
except Exception:
    raise SystemExit("VIRHE: CHANNEL_ID ei ole kelvollinen kokonaisluku (chat id).")

# --- logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- parametrit (muokattavissa komennolla) ---
hours_window = 1.0      # lähetysväli tunteina (float), oletus 1 tunti
top_percent = 5         # ei tällä yksinkertaisella versiolla käytössä mutta pidetään komennolle

# --- Luo telegram application ---
telegram_app = Application.builder().token(BOT_TOKEN).updater(None).build()


# ---- Komennot ----
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Testi: botti vastaanottaa komentoja ja on webhook-tilassa.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"ℹ️ Parametrit:\nLähetysväli: {hours_window} tuntia\nTop % (konfiguroitavissa): {top_percent}%"
    )

async def set_hours_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global hours_window
    try:
        val = float(context.args[0])
        if not (0.1 <= val <= 24):
            raise ValueError("Ei sallitulla alueella")
        hours_window = val
        await update.message.reply_text(f"✅ Aikaväli asetettu: {hours_window} tuntia.")
    except Exception:
        await update.message.reply_text("⚠️ Käyttö: /set_hours <tunnit>  (0.1 - 24)")

async def set_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global top_percent
    try:
        val = int(context.args[0])
        if not (1 <= val <= 100):
            raise ValueError()
        top_percent = val
        await update.message.reply_text(f"✅ Top % asetettu: {top_percent}%.")
    except Exception:
        await update.message.reply_text("⚠️ Käyttö: /set_top_percent <prosentti>  (1 - 100)")

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmds = [
        "/test — testaa että botti vastaa",
        "/status — näyttää nykyiset parametrit",
        "/set_hours <float> — aseta lähetysväli tunneissa (0.1–24)",
        "/set_top_percent <int> — aseta top-prosentti (1–100)",
        "/commands — listaa komennot"
    ]
    await update.message.reply_text("📋 Komennot:\n" + "\n".join(cmds))

# Lisää handlerit
telegram_app.add_handler(CommandHandler("test", test_command))
telegram_app.add_handler(CommandHandler("status", status_command))
telegram_app.add_handler(CommandHandler("set_hours", set_hours_command))
telegram_app.add_handler(CommandHandler("set_top_percent", set_top_command))
telegram_app.add_handler(CommandHandler("commands", commands_command))

# ---- Signaalien haku (Solscan, asynkinen) ----
async def fetch_new_tokens(limit: int = 20):
    # Julkinen Solscan-endpoint: listaa tokeneita uusimmasta
    url = f"https://public-api.solscan.io/token/list?sortBy=createdBlock&direction=desc&limit={limit}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
        if r.status_code == 200:
            return r.json()
        else:
            logging.warning("Solscan palautti ei-200: %s %s", r.status_code, r.text[:200])
            return []

async def signal_loop_async():
    """Taustatehtävä: hakee uusia tokeneita ja lähettää tiivistelmän kanavaan."""
    await asyncio.sleep(2)  # pieni viive käynnistyksen jälkeen
    while True:
        try:
            tokens = await fetch_new_tokens(limit=20)
            if not tokens:
                logging.info("Ei uusia tokeneita tällä kierroksella.")
            else:
                text = "📊 Uudet tokenit Solana (viimeisin lista):\n"
                for t in tokens:
                    sym = t.get("symbol") or t.get("tokenSymbol") or "N/A"
                    addr = t.get("tokenAddress") or t.get("address") or ""
                    name = t.get("tokenName") or ""
                    text += f"- {sym} {name} ({addr})\n"
                # Lähetä viesti kanavaan
                try:
                    await telegram_app.bot.send_message(chat_id=CHANNEL_ID, text=text)
                    logging.info("Signaali lähetetty: %d tokenia", len(tokens))
                except Exception as e:
                    logging.exception("Virhe viestin lähetyksessä: %s", e)
        except Exception:
            logging.exception("Virhe signaalisilmukassa:")
        # odota seuraavaan kierrokseen
        await asyncio.sleep(max(0.1, hours_window) * 3600)

# ---- Webhook endpoint (aiohttp) ----
async def telegram_webhook(request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Bad request")
    update = Update.de_json(data, telegram_app.bot)
    # laita päivitys telegram_app:in update_queue:hin käsittelyä varten
    await telegram_app.update_queue.put(update)
    return web.Response(text="OK")

# ---- Main: käynnistys, webhookin rekisteröinti ja aiohttp-palvelin ----
async def main():
    webhook_url = APP_URL.rstrip("/") + WEBHOOK_PATH
    logging.info("Käynnistetään bot (webhook -> %s) portissa %s", webhook_url, PORT)

    # initialize ja set webhook
    await telegram_app.initialize()
    # Poista vanhat päivitykset ja aseta webhook Telegramiin
    try:
        await telegram_app.bot.set_webhook(webhook_url, drop_pending_updates=True)
        logging.info("Webhook asetettu: %s", webhook_url)
    except Exception:
        logging.exception("Webhook-asetuksessa virhe:")

    # Käynnistä telegram dispatcher / sisäinen käsittely (ilman pollingia)
    await telegram_app.start()

    # käynnistä taustatehtävät
    asyncio.create_task(signal_loop_async())

    # aiohttp - pieni web-palvelin vastaanottamaan POST /webhook
    web_app = web.Application()
    web_app.router.add_post(WEBHOOK_PATH, telegram_webhook)
    web_app.router.add_get("/", lambda request: web.Response(text="OK"))

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info("Webhook-palvelin käynnissä (listening).")

    # Odotetaan pysyvästi (lopetetaan CTRL+C tai Render SIGTERM:llä)
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        logging.info("Suljetaan palvelu...")
        await runner.cleanup()
        await telegram_app.shutdown()
        await telegram_app.stop()

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = telegram_app.update_queue_factory().json_to_update(request.json, telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
