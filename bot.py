import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Aseta oma bottitoken tähän
BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

# Loggeri, että nähdään virheet Renderissä
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# /start -komento
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hei! Olen toiminnassa ✅ Käytä /commands nähdäksesi komennot."
    )

# /test -komento
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Testiviesti toimii! ✅")

# /commands -komento
async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd_list = (
        "📋 Käytettävissä olevat komennot:\n\n"
        "/start - Käynnistää botin\n"
        "/test - Testaa vastaako botti\n"
        "/commands - Näytä tämä komentolista\n"
    )
    await update.message.reply_text(cmd_list)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Rekisteröidään komennot
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("commands", commands))

    # Käynnistetään polling yhdellä instanssilla, pudotetaan vanhat viestit
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
