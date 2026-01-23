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

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

# ===== MENU =====
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🧮 Máy tính"],
        ["💱 Tỷ giá", "💰 Phí %"],
        ["🇻🇳 VN", "🇨🇳 CN"],
        ["❌ Đóng"],
    ],
    resize_keyboard=True,
)

# ===== DATA THEO GROUP =====
GROUPS = {}  # chat_id -> state


def is_admin(update: Update) -> bool:
    uid = update.effective_user.id
    if uid == OWNER_ID:
        return True
    try:
        m = update.effective_chat.get_member(uid)
        return m.status in ("administrator", "creator")
    except:
        return False


def get_group(chat_id):
    if chat_id not in GROUPS:
        GROUPS[chat_id] = {
            "rate": None,
            "fee": 0.0,
            "lang": "VN",
            "mode": None,  # rate | fee | None
            "rows": [],  # list of numbers (+ / -)
        }
    return GROUPS[chat_id]


# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text(
        "🤖 BOT TÍNH BILL NHÓM", reply_markup=MAIN_MENU
    )


# ===== HANDLE MENU & TEXT =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    g = get_group(chat_id)

    if text == "🧮 Máy tính":
        g["mode"] = None
        await update.message.reply_text("Nhập + / - để cộng trừ", reply_markup=MAIN_MENU)

    elif text == "💱 Tỷ giá":
        g["mode"] = "rate"
        await update.message.reply_text("Nhập tỷ giá")

    elif text == "💰 Phí %":
        g["mode"] = "fee"
        await update.message.reply_text("Nhập phí (%)")

    elif text == "🇻🇳 VN":
        g["lang"] = "VN"
        await update.message.reply_text("Đã chuyển ngôn ngữ: VN")

    elif text == "🇨🇳 CN":
        g["lang"] = "CN"
        await update.message.reply_text("已切换语言：中文")

    elif text == "❌ Đóng":
        await update.message.reply_text("Đã đóng menu")

    else:
        await handle_number(update, g)


# ===== HANDLE NUMBER INPUT =====
async def handle_number(update: Update, g):
    raw = update.message.text.replace(",", "").strip()

    # set rate
    if g["mode"] == "rate":
        try:
            g["rate"] = float(raw)
            g["mode"] = None
            await update.message.reply_text(f"✅ Đã đặt tỷ giá: {g['rate']}")
        except:
            await update.message.reply_text("❌ Tỷ giá không hợp lệ")
        return

    # set fee
    if g["mode"] == "fee":
        try:
            g["fee"] = float(raw)
            g["mode"] = None
            await update.message.reply_text(f"✅ Đã đặt phí: {g['fee']}%")
            await render_bill(update, g)
        except:
            await update.message.reply_text("❌ Phí không hợp lệ")
        return

    # handle + / -
    if raw.startswith(("+", "-")):
        try:
            val = float(raw)
            if val == 0:
                g["rows"] = []
            else:
                if g["rate"] is None:
                    await update.message.reply_text("⚠️ Chưa đặt tỷ giá")
                    return
                g["rows"].append(val)
            await render_bill(update, g)
        except:
            pass


# ===== RENDER BILL =====
async def render_bill(update: Update, g):
    rate = g["rate"]
    fee = g["fee"]
    rows = g["rows"]

    total_in = 0.0
    total_out = 0.0
    lines = []

    for v in rows:
        usdt = abs(v) / rate
        t = datetime.now().strftime("%H:%M")
        if v > 0:
            total_in += usdt
            lines.append(f"{t}  {int(v)} / {rate} = {round(usdt,2)} USDT")
        else:
            total_out += usdt
            lines.append(f"{t}  -{int(abs(v))} USDT")

    balance = total_in - total_out
    fee_value = balance * fee / 100 if fee > 0 else 0
    balance_after = balance - fee_value

    now = datetime.now().strftime("%d/%m/%Y – %H:%M")

    if g["lang"] == "VN":
        msg = [
            "🧾 HÓA ĐƠN",
            f"👤 Người tạo: TianLong",
            f"🕒 Thời gian: {now}",
            "",
        ]
    else:
        msg = [
            "🧾 账单",
            f"👤 创建者: TianLong",
            f"🕒 时间: {now}",
            "",
        ]

    if lines:
        msg += lines
    else:
        msg.append("📭 Chưa có giao dịch nào được thực hiện")

    msg.append("")

    if fee > 0:
        msg.append(f"💰 Phí: {fee}%")

    msg += [
        "⸻",
        f"📥 Tổng thu: {round(total_in,2)} USDT",
        f"📤 Tổng chi: {round(total_out,2)} USDT",
        f"💰 Số dư: {round(balance_after,2)} USDT",
    ]

    await update.message.reply_text("\n".join(msg))


# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()


if __name__ == "__main__":
    main()
