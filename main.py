import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ========= ENV =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID_RAW = os.getenv("OWNER_ID")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN missing")

OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW and OWNER_ID_RAW.isdigit() else None

# ========= MENUS =========
MAIN_MENU = ReplyKeyboardMarkup(
    [["🧮 Máy tính", "📄 Xem bill"], ["❌ Đóng"]],
    resize_keyboard=True
)

CALC_MENU = ReplyKeyboardMarkup(
    [["💸 Phí %"], ["⬅️ Quay lại"]],
    resize_keyboard=True
)

# ========= DATA =========
DATA: dict[int, dict] = {}

# ========= HANDLERS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Bot Bill sẵn sàng\nChọn chức năng:",
        reply_markup=MAIN_MENU
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    uid = update.message.from_user.id
    text = update.message.text.strip()

    # ---- MAIN MENU ----
    if text == "🧮 Máy tính":
        DATA[uid] = {"rows": [], "fee": 0.0}
        await update.message.reply_text(
            "👉 Nhập giao dịch theo dạng:\n`SỐ / TỶ GIÁ`\nVí dụ: `100000 / 25000`",
            reply_markup=CALC_MENU
        )
        return

    if text == "📄 Xem bill":
        await show_bill(update)
        return

    if text == "⬅️ Quay lại":
        await update.message.reply_text("⬅️ Quay lại menu chính", reply_markup=MAIN_MENU)
        return

    if text == "❌ Đóng":
        DATA.pop(uid, None)
        await update.message.reply_text("❌ Đã đóng phiên", reply_markup=MAIN_MENU)
        return

    # ---- CALC MODE ----
    if uid not in DATA:
        return

    # Set fee
    if text.endswith("%") or text.replace(".", "").isdigit():
        try:
            fee = float(text.replace("%", ""))
            DATA[uid]["fee"] = fee
            await update.message.reply_text(f"✅ Đã đặt phí: {fee}%")
        except ValueError:
            await update.message.reply_text("❌ Phí không hợp lệ")
        return

    # Add transaction
    try:
        money, rate = text.split("/")
        usdt = float(money.strip()) / float(rate.strip())
        DATA[uid]["rows"].append(usdt)
        await update.message.reply_text(
            f"➕ Đã thêm: {usdt:.2f} USDT"
        )
    except Exception:
        await update.message.reply_text("❌ Sai định dạng\nDùng: `SỐ / TỶ GIÁ`")

async def show_bill(update: Update):
    uid = update.message.from_user.id
    data = DATA.get(uid)

    if not data or not data["rows"]:
        await update.message.reply_text("📭 Chưa có dữ liệu")
        return

    total = sum(data["rows"])
    fee = data["fee"]
    fee_value = total * fee / 100
    balance = total - fee_value

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        "🧾 HÓA ĐƠN",
        f"🕒 {now}",
        ""
    ]

    for i, v in enumerate(data["rows"], 1):
        lines.append(f"Giao dịch {i}: {v:.2f} USDT")

    if fee > 0:
        lines.append(f"Phí: {fee}% (-{fee_value:.2f} USDT)")

    lines += [
        "------------------",
        f"💰 Tổng: {total:.2f} USDT",
        f"✅ Nhận: {balance:.2f} USDT"
    ]

    await update.message.reply_text("\n".join(lines))

# ========= MAIN =========
def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("✅ Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
