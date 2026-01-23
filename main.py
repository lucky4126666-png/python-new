import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

# ====== MENU ======
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📜 Quản lý nhóm"],
        ["🧮 Máy tính"],
        ["❌ Đóng"]
    ],
    resize_keyboard=True
)

CALC_MENU = ReplyKeyboardMarkup(
    [
        ["🔢 Tỷ giá", "💸 Phí %"],
        ["🌐 VN | CN"],
        ["⬅️ Quay lại"]
    ],
    resize_keyboard=True
)

# ====== DATA (theo GROUP) ======
DATA = {}

def is_admin(update: Update) -> bool:
    uid = update.effective_user.id
    if uid == OWNER_ID:
        return True
    member = update.effective_chat.get_member(uid)
    return member.status in ("administrator", "creator")

def get_group(chat_id):
    if chat_id not in DATA:
        DATA[chat_id] = {
            "rate": None,
            "fee": 0.0,
            "rows": [],
            "lang": "VN"
        }
    return DATA[chat_id]

# ====== START ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text("Bot Bill sẵn sàng", reply_markup=MAIN_MENU)

# ====== HANDLE TEXT ======
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    group = get_group(chat_id)

    if text == "🧮 Máy tính":
        await update.message.reply_text("Máy tính", reply_markup=CALC_MENU)

    elif text == "🔢 Tỷ giá":
        await update.message.reply_text("Nhập tỷ giá")

    elif text == "💸 Phí %":
        await update.message.reply_text("Nhập phí %")

    elif text == "🌐 VN | CN":
        group["lang"] = "CN" if group["lang"] == "VN" else "VN"
        await update.message.reply_text(f"Đã đổi ngôn ngữ: {group['lang']}")

    elif text == "⬅️ Quay lại":
        await update.message.reply_text("Menu chính", reply_markup=MAIN_MENU)

    elif text == "❌ Đóng":
        await update.message.reply_text("Đã đóng menu")

    else:
        await handle_number(update, context)

# ====== XỬ LÝ SỐ ======
async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.replace(",", "").strip()
    group = get_group(chat_id)

    # set tỷ giá / phí
    if group["rate"] is None:
        try:
            group["rate"] = float(text)
            await update.message.reply_text(f"Đã đặt tỷ giá: {group['rate']}")
        except:
            pass
        return

    if text.replace(".", "").isdigit():
        group["fee"] = float(text)
        await update.message.reply_text(f"Đã đặt phí: {group['fee']}%")
        return

    # + / -
    if text.startswith(("+", "-")):
        try:
            value = float(text)
            if value == 0:
                group["rows"] = []
            else:
                group["rows"].append(value)
            await render_bill(update, group)
        except:
            pass

# ====== IN BILL ======
async def render_bill(update: Update, group):
    rate = group["rate"]
    fee = group["fee"]
    rows = group["rows"]

    total_usdt = 0
    lines = []

    for v in rows:
        usdt = v / rate
        total_usdt += usdt
        lines.append(f"{int(v)} / {rate} = {round(usdt,2)} USDT")

    fee_value = total_usdt * fee / 100
    balance = total_usdt - fee_value

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    if group["lang"] == "VN":
        msg = [
            "HÓA ĐƠN",
            f"Thời gian: {now}",
            ""
        ]
    else:
        msg = [
            "账单",
            f"时间: {now}",
            ""
        ]

    if lines:
        msg += lines
    else:
        msg.append("[ chưa có giao dịch nào được thực hiện ]")

    if fee > 0:
        msg.append(f"Phí: {fee}% ({round(fee_value,2)} USDT)")

    msg += [
        "------------------",
        f"Tổng: {round(total_usdt,2)} USDT",
        f"Số dư: {round(balance,2)} USDT"
    ]

    await update.message.reply_text("\n".join(msg))

# ====== MAIN ======
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()

if __name__ == "__main__":
    main()
