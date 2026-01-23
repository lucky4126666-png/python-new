import os
import pytz
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_OWNER_ID = int(os.getenv("OWNER_ID", "0"))
VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

if not BOT_TOKEN or not BOT_OWNER_ID:
    raise RuntimeError("Missing BOT_TOKEN or OWNER_ID")

# ========= DATA =========
GROUP_DATA = {}       # chat_id → bill data
WHITELIST = {}        # chat_id → set(user_id)
ADMINS = set()        # admin ids (added by owner)
PENDING = {}          # pending confirm actions

# ========= MENUS =========
MAIN_MENU = ReplyKeyboardMarkup(
    [["🧮 Máy tính"], ["❌ Đóng"]],
    resize_keyboard=True
)

CALC_MENU = ReplyKeyboardMarkup(
    [
        ["🔢 Tỷ giá", "💸 Phí %"],
        ["🇻🇳 VN", "🇨🇳 CN"],
        ["⬅️ Quay lại"]
    ],
    resize_keyboard=True
)

OWNER_MENU = ReplyKeyboardMarkup(
    [
        ["➕ Thêm whitelist", "➖ Xóa whitelist"],
        ["⬅️ Quay lại"]
    ],
    resize_keyboard=True
)

CONFIRM_MENU = ReplyKeyboardMarkup(
    [["✅ Xác nhận", "❌ Hủy"]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ========= HELPERS =========
def now_vn():
    return datetime.now(VN_TZ).strftime("%d/%m/%Y – %H:%M")

def is_allowed(chat_id, uid):
    return (
        uid == BOT_OWNER_ID or
        uid in ADMINS or
        uid in WHITELIST.get(chat_id, set())
    )

def init_group(chat_id):
    GROUP_DATA.setdefault(chat_id, {
        "rate": None,
        "fee": 0.0,
        "in": 0.0,
        "out": 0.0,
        "lang": "VN"
    })

def render_bill(chat_id, creator):
    d = GROUP_DATA[chat_id]
    fee_text = f"{d['fee']}%" if d["fee"] > 0 else "0%"
    balance = d["in"] - d["out"]

    if d["lang"] == "CN":
        return (
            f"🧾 账单\n\n"
            f"👤 创建者: {creator}\n"
            f"🕒 时间: {now_vn()}\n\n"
            f"📥 收入: {round(d['in'],2)} USDT\n"
            f"📤 支出: {round(d['out'],2)} USDT\n"
            f"💸 手续费: {fee_text}\n"
            f"💰 余额: {round(balance,2)} USDT"
        )

    return (
        f"🧾 HÓA ĐƠN\n\n"
        f"👤 Người tạo: {creator}\n"
        f"🕒 Thời gian: {now_vn()}\n\n"
        f"📥 Tổng thu: {round(d['in'],2)} USDT\n"
        f"📤 Tổng chi: {round(d['out'],2)} USDT\n"
        f"💸 Phí: {fee_text}\n"
        f"💰 Số dư: {round(balance,2)} USDT"
    )

# ========= HANDLERS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != BOT_OWNER_ID:
        return
    await update.message.reply_text("🤖 BOT SẴN SÀNG", reply_markup=MAIN_MENU)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = msg.from_user.id
    chat_id = msg.chat_id
    text = msg.text.strip()

    if not is_allowed(chat_id, uid):
        return

    init_group(chat_id)

    # OWNER WHITELIST MENU
    if uid == BOT_OWNER_ID:
        if text == "➕ Thêm whitelist":
            PENDING[uid] = {"action": "add", "chat": chat_id}
            await msg.reply_text("Gửi ID cần THÊM")
            return

        if text == "➖ Xóa whitelist":
            PENDING[uid] = {"action": "remove", "chat": chat_id}
            await msg.reply_text("Gửi ID cần XÓA")
            return

    # CONFIRM
    if uid in PENDING:
        p = PENDING[uid]
        if text.isdigit():
            p["target"] = int(text)
            await msg.reply_text("Xác nhận thao tác?", reply_markup=CONFIRM_MENU)
            return

        if text == "❌ Hủy":
            PENDING.pop(uid)
            await msg.reply_text("Đã hủy")
            return

        if text == "✅ Xác nhận":
            WHITELIST.setdefault(p["chat"], set())
            if p["action"] == "add":
                WHITELIST[p["chat"]].add(p["target"])
                await msg.reply_text("Đã thêm whitelist")
            else:
                WHITELIST[p["chat"]].discard(p["target"])
                await msg.reply_text("Đã xóa whitelist")
            PENDING.pop(uid)
            return

    d = GROUP_DATA[chat_id]

    # MENUS
    if text == "🧮 Máy tính":
        await msg.reply_text("Menu máy tính", reply_markup=CALC_MENU)
        return

    if text == "⬅️ Quay lại":
        if uid == BOT_OWNER_ID:
            await msg.reply_text("Menu", reply_markup=MAIN_MENU)
        return

    if text == "❌ Đóng":
        await msg.reply_text("Đã đóng menu")
        return

    # SETTINGS
    if text == "🔢 Tỷ giá":
        await msg.reply_text("Nhập tỷ giá")
        context.user_data["set"] = "rate"
        return

    if text == "💸 Phí %":
        await msg.reply_text("Nhập phí %")
        context.user_data["set"] = "fee"
        return

    if text == "🇻🇳 VN":
        d["lang"] = "VN"
        await msg.reply_text("Đã chuyển VN")
        return

    if text == "🇨🇳 CN":
        d["lang"] = "CN"
        await msg.reply_text("已切换中文")
        return

    # INPUT NUMBER
    if context.user_data.get("set") == "rate":
        d["rate"] = float(text)
        context.user_data.clear()
        await msg.reply_text("Đã đặt tỷ giá")
        return

    if context.user_data.get("set") == "fee":
        d["fee"] = float(text)
        context.user_data.clear()
        await msg.reply_text("Đã đặt phí")
        return

    # TRANSACTION
    if text.startswith(("+", "-")):
        if text in ("+0", "-0"):
            d["in"] = d["out"] = 0
        else:
            amount = float(text[1:]) / d["rate"]
            if text.startswith("+"):
                d["in"] += amount
            else:
                d["out"] += amount

        await msg.reply_text(render_bill(chat_id, msg.from_user.first_name))
        return

# ========= RUN =========
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()

if __name__ == "__main__":
    main()
