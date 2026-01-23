import os
from datetime import datetime, timezone, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
OWNER_ID = 8572604188  # 👈 SỬA ID CHỦ BOT

ADMINS = {OWNER_ID}
pending_admin_action = {}

groups = {}
# groups[gid] = {
#   rate, lang, inputs, outputs
# }

# ================= TIME =================
def now_vn_time():
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz).strftime("%H:%M")

def now_vn_date():
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz).strftime("%d/%m/%Y")

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
    date = now_vn_date()

    total_in = sum(i["usdt"] for i in g["inputs"])
    total_out = sum(g["outputs"])
    balance = total_in - total_out

    lines = []
    lines.append(f"🧾 HÓA ĐƠN | {date}\n")
    lines.append(f"👤 Người tạo: {name}\n")
    lines.append("⸻\n")

    lines.append(f"Nhập ({len(g['inputs'])})")
    for i in g["inputs"]:
        lines.append(
            f"{i['time']} | {i['vnd']:,.0f} / {i['rate']} = {i['usdt']:,.2f} USDT"
        )

    lines.append("\n⸻\n")

    lines.append(f"Xuất ({len(g['outputs'])})")
    for o in g["outputs"]:
        lines.append(f"-{o:,.2f} USDT")

    lines.append("\n⸻\n")
    lines.append(f"+ Nhập : {total_in:,.2f} USDT")
    lines.append(f"- Xuất : {total_out:,.2f} USDT")
    lines.append(f"💰 Tổng cộng : {balance:,.2f} USDT")

    return "\n".join(lines)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    await update.message.reply_text("🤖 BOT TÍNH BILL", reply_markup=MAIN_MENU)

# ================= HANDLER =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    user = update.effective_user
    chat = update.effective_chat

    uid = user.id
    gid = chat.id
    name = user.first_name

    if uid not in ADMINS:
        return

    if gid not in groups:
        groups[gid] = {
            "rate": 1.0,
            "lang": "VN",
            "inputs": [],
            "outputs": []
        }

    g = groups[gid]

    # ===== MENU =====
    if msg == "🧮 Máy tính":
        await update.message.reply_text("🧮 Máy tính", reply_markup=CALC_MENU)
        return

    if msg == "⬅️ Quay lại":
        await update.message.reply_text("Menu chính", reply_markup=MAIN_MENU)
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

    # ===== RESET =====
    if msg in ["+0", "-0"]:
        g["inputs"].clear()
        g["outputs"].clear()
        await update.message.reply_text(render_bill(name, g))
        return

    # ===== INPUT =====
    if msg.startswith("+"):
        try:
            vnd = float(msg[1:])
            usdt = round(vnd / g["rate"], 2)
            g["inputs"].append({
                "time": now_vn_time(),
                "vnd": vnd,
                "rate": g["rate"],
                "usdt": usdt
            })
            await update.message.reply_text(render_bill(name, g))
        except:
            pass
        return

    # ===== OUTPUT =====
    if msg.startswith("-"):
        try:
            usdt = float(msg[1:])
            g["outputs"].append(usdt)
            await update.message.reply_text(render_bill(name, g))
        except:
            pass
        return

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == "__main__":
    main()
