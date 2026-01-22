from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Railway chạy OK 🚄")

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN chưa được set")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("Bot đang chạy trên Railway...")
    app.run_polling()

if __name__ == "__main__":
    main()
