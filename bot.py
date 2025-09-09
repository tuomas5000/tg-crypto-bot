# bot.py
import os
import asyncio
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from aiohttp import web

# --- Konfiguraatio ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID_ENV = os.environ.get("CHANNEL_ID")
APP_URL = os.environ.get("APP_URL")
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")
PORT = int(os.environ.get("PORT", "8080"))

if not BOT_TOKEN or not CHANNEL_ID_ENV or not APP_URL:
    raise SystemExit("VIRHE: Aseta BOT_TOKEN, CHANNEL_ID ja APP_URL.")

try:
    CHANNEL_ID = int(CHANNEL_ID_ENV)
except Exception:
    raise SystemExit("VIRHE: CHANNEL_ID ei kelpaa.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- Parametrit ---
hours_window = 1.0
top_percent = 5

# --- Telegram Application ---
telegram_app = Application.builder().token(BOT_TOKEN).updater(None).build()

# --- Komennot ---
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Testi: botti vastaanottaa komentoja.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"ℹ️ Parametrit:\nLähetysväli: {hours_window} tuntia\nTop %: {top_percent}%"
    )

async def set_hours_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global hours_window
    try:
        val = float(context.args[0])
        if not (0.1 <= val <= 24):
            raise ValueError()
        hours_window = val
        await update.message.reply_text(f"✅ Aikaväli asetettu: {hours_window} tuntia.")
    except Exception:
        await update.message.reply_text("⚠️ Käyttö: /set_hours <tunnit> (0.1–24)")

async def set_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global top_percent
    try:
        val = int(context.args[0])
        if not (1 <= val <= 100):
            raise ValueError()
        top_percent = val
        await update.message.reply_text(f"✅ Top % asetettu: {top_percent}%.")
    except Exception:
        await update.message.reply_text("⚠️ Käyttö: /set_top_percent <prosentti> (1–100)")

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmds = [
        "/test — testaa bottia",
        "/status — näyttää parametrit",
        "/set_hours <float> — aseta lähetysväli (0.1–24)",
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

# --- Signaalien haku ---
async def fetch_new_tokens(limit: int = 20):
    url = f"https://public-api.solscan.io/token/list?sortBy=createdBlock&direction=desc&limit={limit}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
        if r.status_code == 200:
            return r.json()
        return []

async def signal_loop_async():
    await asyncio.sleep(2)
    while True:
        tokens = await fetch_new_tokens(limit=20)
        if tokens:
            text = "📊 Uudet tokenit:\n"
            for t in tokens:
                sym = t.get("symbol") or t.get("tokenSymbol") or "N/A"
                addr = t.get("tokenAddress") or t.get("address") or ""
                text += f"- {sym} ({addr})\n"
            try:
                await telegram_app.bot.send_message(chat_id=CHANNEL_ID, text=text)
            except Exception:
                logging.exception("Virhe viestin lähetyksessä")
        await asyncio.sleep(max(0.1, hours_window) * 3600)

# --- Webhook aiohttp ---
async def telegram_webhook(request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Bad request")
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.update_queue.put(update)
    return web.Response(text="OK")

async def main():
    webhook_url = APP_URL.rstrip("/") + WEBHOOK_PATH
    logging.info("Käynnistetään bot (webhook -> %s) portissa %s", webhook_url, PORT)

    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(webhook_url, drop_pending_updates=True)
    await telegram_app.start()
    asyncio.create_task(signal_loop_async())

    web_app = web.Application()
    web_app.router.add_post(WEBHOOK_PATH, telegram_webhook)
    web_app.router.add_get("/", lambda request: web.Response(text="Bot webhook aktiivinen"))

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    stop_event = asyncio.Event()
    await stop_event.wait()

if __name__ == "__main__":
    asyncio.run(main())
