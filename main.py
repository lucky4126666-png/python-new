import os
from datetime import datetime, timezone, timedelta

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
OWNER_ID = 123456789  # 👈 ID chủ bot (BẮT BUỘC SỬA)

ADMINS = {OWNER_ID}
pending_admin_action = {}

groups = {}
# groups[gid] = {
#   balance, income, expense, fee, rate, lang
# }

# ================= TIME =================
def now_vn():
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz).strftime("%d/%m/%Y – %H:%M")

# ================= MENUS =================
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📜 Quản lý nhóm"],
        ["🧮 Máy tính"],
        ["👑 Admin"],
        ["❌ Đóng"]
    ],
    resize_keyboard=True
)

CALC_MENU = ReplyKeyboardMarkup(
    [
        ["🔢 Tỷ giá", "💸 Phí %"],
        ["VN | 🇻🇳", "CN | 🇨🇳"],
        ["⬅️ Quay lại"]
    ],
    resize_keyboard=True
)

ADMIN_MENU = ReplyKeyboardMarkup(
    [
        ["➕ Thêm Admin"],
        ["➖ Xóa Admin"],
        ["📋 Danh sách Admin"],
        ["⬅️ Quay lại"]
    ],
    resize_keyboard=True
)

CONFIRM_MENU = ReplyKeyboardMarkup(
    [
        ["✅ Xác nhận"],
        ["❌ Hủy"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ================= BILL =================
def render_bill(name, g):
    time = now_vn()

    if g["lang"] == "CN":
        return (
            f"📄 <b>账单</b>\n\n"
            f"👤 创建者: {name}\n"
            f"🕒 时间: {time}\n\n"
            f"📥 收入: {g['income']:.2f} USDT\n"
            f"📤 支出: {g['expense']:.2f} USDT\n"
            f"💸 手续费: {g['fee']}%\n"
            f"💰 余额: <b>{g['balance']:.2f} USDT</b>"
        )

    return (
        f"🧾 <b>HÓA ĐƠN</b>\n\n"
        f"👤 Người tạo: {name}\n"
        f"🕒 Thời gian: {time}\n\n"
        f"📥 Tổng thu: {g['income']:.2f} USDT\n"
        f"📤 Tổng chi: {g['expense']:.2f} USDT\n"
        f"💸 Phí: {g['fee']}%\n"
        f"💰 Số dư: <b>{g['balance']:.2f} USDT</b>"
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in ADMINS:
        return

    await update.message.reply_text(
        "🤖 BOT TÍNH BILL",
        reply_markup=MAIN_MENU
    )

# ================= HANDLER =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    user = update.effective_user
    chat = update.effective_chat

    uid = user.id
    gid = chat.id
    name = user.first_name

    # 🔐 ONLY ADMIN
    if uid not in ADMINS:
        return

    if gid not in groups:
        groups[gid] = {
            "balance": 0.0,
            "income": 0.0,
            "expense": 0.0,
            "fee": 0,
            "rate": 1,
            "lang": "VN"
        }

    g = groups[gid]

    # ===== MAIN MENU =====
    if msg == "📜 Quản lý nhóm":
        await update.message.reply_text("📜 Quản lý nhóm")
        return

    if msg == "🧮 Máy tính":
        await update.message.reply_text("🧮 Máy tính", reply_markup=CALC_MENU)
        return

    if msg == "👑 Admin":
        if uid != OWNER_ID:
            return
        await update.message.reply_text("👑 Quản lý Admin", reply_markup=ADMIN_MENU)
        return

    if msg == "❌ Đóng":
        await update.message.reply_text("❌ Đã đóng menu", reply_markup=None)
        return

    # ===== BACK =====
    if msg == "⬅️ Quay lại":
        await update.message.reply_text("⬅️ Menu chính", reply_markup=MAIN_MENU)
        return

    # ===== LANGUAGE =====
    if msg.startswith("VN"):
        g["lang"] = "VN"
        await update.message.reply_text("🇻🇳 Đã chuyển Tiếng Việt")
        return

    if msg.startswith("CN"):
        g["lang"] = "CN"
        await update.message.reply_text("🇨🇳 已切换中文")
        return

    # ===== RATE =====
    if msg == "🔢 Tỷ giá":
        context.user_data["set_rate"] = True
        await update.message.reply_text("Nhập tỷ giá:")
        return

    if context.user_data.get("set_rate"):
        try:
            g["rate"] = float(msg)
            context.user_data["set_rate"] = False
            await update.message.reply_text("✅ Đã đặt tỷ giá")
        except:
            await update.message.reply_text("❌ Tỷ giá không hợp lệ")
        return

    # ===== FEE =====
    if msg == "💸 Phí %":
        context.user_data["set_fee"] = True
        await update.message.reply_text("Nhập % phí:")
        return

    if context.user_data.get("set_fee"):
        try:
            g["fee"] = int(msg)
            context.user_data["set_fee"] = False
            await update.message.reply_text("✅ Đã đặt phí")
        except:
            await update.message.reply_text("❌ Phí không hợp lệ")
        return

    # ===== RESET =====
    if msg in ["+0", "-0"]:
        g["balance"] = 0
        g["income"] = 0
        g["expense"] = 0
        await update.message.reply_text(render_bill(name, g), parse_mode="HTML")
        return

    # ===== ADD / SUB =====
    if msg.startswith("+"):
        try:
            vnd = float(msg[1:])
            usdt = vnd / g["rate"]
            g["income"] += usdt
            g["balance"] += usdt
            await update.message.reply_text(render_bill(name, g), parse_mode="HTML")
        except:
            pass
        return

    if msg.startswith("-"):
        try:
            vnd = float(msg[1:])
            usdt = vnd / g["rate"]
            g["expense"] += usdt
            g["balance"] -= usdt
            await update.message.reply_text(render_bill(name, g), parse_mode="HTML")
        except:
            pass
        return

    # ===== ADMIN PANEL =====
    if uid == OWNER_ID and msg == "➕ Thêm Admin":
        pending_admin_action[uid] = {"action": "add"}
        await update.message.reply_text("Gửi ID cần THÊM admin", reply_markup=CONFIRM_MENU)
        return

    if uid == OWNER_ID and msg == "➖ Xóa Admin":
        pending_admin_action[uid] = {"action": "remove"}
        await update.message.reply_text("Gửi ID cần XÓA admin", reply_markup=CONFIRM_MENU)
        return

    if uid == OWNER_ID and msg == "📋 Danh sách Admin":
        text = "👑 DANH SÁCH ADMIN\n\n"
        for a in ADMINS:
            text += f"• {a}\n"
        await update.message.reply_text(text)
        return

    if uid == OWNER_ID and uid in pending_admin_action and msg.isdigit():
        pending_admin_action[uid]["target"] = int(msg)
        await update.message.reply_text("⚠️ Xác nhận thao tác?", reply_markup=CONFIRM_MENU)
        return

    if uid == OWNER_ID and msg == "✅ Xác nhận":
        action = pending_admin_action[uid]["action"]
        target = pending_admin_action[uid]["target"]

        if action == "add":
            ADMINS.add(target)
            text = "✅ Đã thêm Admin"
        else:
            if target != OWNER_ID:
                ADMINS.discard(target)
                text = "✅ Đã xóa Admin"
            else:
                text = "❌ Không thể xóa OWNER"

        pending_admin_action.pop(uid)
        await update.message.reply_text(text, reply_markup=ADMIN_MENU)
        return

    if uid == OWNER_ID and msg == "❌ Hủy":
        pending_admin_action.pop(uid, None)
        await update.message.reply_text("❌ Đã hủy", reply_markup=ADMIN_MENU)
        return

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == "__main__":
    main()
