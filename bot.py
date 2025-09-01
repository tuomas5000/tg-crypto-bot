import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Aseta Renderin environment variableihin

# ===== Komennot =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Moi! Olen signaalibotti. Käytä /commands nähdäksesi listan komennoista.")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Botti toimii ja vastaa komentoihin!")

async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd_list = (
        "📋 Käytettävät komennot:\n\n"
        "/start - Käynnistä botti\n"
        "/test - Testaa bottia\n"
        "/commands - Näytä kaikki komennot\n"
        "/signal - Lähetä esimerkkisignaali"
    )
    await update.message.reply_text(cmd_list)

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Tämä on placeholder, myöhemmin tähän liitetään oikeat top 5% coinit Solscanista
    await update.message.reply_text("🚀 Esimerkkisignaali: Coin XYZ, ostajamäärä kasvanut 120% viime tunnissa.")

# ===== Taustalooppi signaaleille =====

async def signal_loop(application: Application):
    while True:
        try:
            # myöhemmin tähän lisätään Solscan-haku ja top 5% -filtteri
            await application.bot.send_message(
                chat_id=os.getenv("CHANNEL_ID"),
                text="📡 Taustasignaali: Coin ABC - dummy testiviesti."
            )
        except Exception as e:
            print(f"Virhe signaaliloopissa: {e}")

        await asyncio.sleep(3600)  # 1h välein

# ===== Main =====

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Komennot
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("commands", commands))
    app.add_handler(CommandHandler("signal", signal))

    # Käynnistä taustalooppi
    async def on_startup():
        asyncio.create_task(signal_loop(app))

  app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
