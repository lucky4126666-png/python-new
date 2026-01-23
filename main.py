import os
from datetime import datetime, timezone, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
TOKEN = "YOUR_BOT_TOKEN_HERE"
OWNER_ID = 8572604188  # ID của bạn

SUPER_ADMINS = {OWNER_ID}
GROUP_ADMINS = {}
groups = {}

# ================= TIME =================
def tz_vn():
    return timezone(timedelta(hours=7))

def today():
    return datetime.now(tz_vn()).strftime("%d/%m/%Y")

def now_time():
    return datetime.now(tz_vn()).strftime("%H:%M")

# ================= ADMIN =================
def is_admin(uid, gid):
    return uid in SUPER_ADMINS or uid in GROUP_ADMINS.get(gid, set())

# ================= MENU =================
MAIN_MENU_TEXT = (
    "━━━━━━━━━━━━━━━━━━\n"
    "🐉  TIANLONG BOT\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "📌 MENU CHÍNH"
)

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Quản lý nhóm", callback_data="group")],
        [InlineKeyboardButton("🧮 Máy tính", callback_data="calc")],
        [InlineKeyboardButton("👑 Admin", callback_data="admin")],
        [InlineKeyboardButton("❌ Đóng", callback_data="close")]
    ])

def admin_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Thêm Admin", callback_data="add_admin")],
        [InlineKeyboardButton("➖ Xóa Admin", callback_data="remove_admin")],
        [InlineKeyboardButton("⬅️ Quay lại", callback_data="back")]
    ])

# ================= BILL =================
def render_bill(name, g):
    tin = sum(i["usdt"] for i in g["inputs"])
    tout = sum(o["usdt"] for o in g["outputs"])
    total = tin - tout

    lines = [
        f"🧾 HÓA ĐƠN | {today()}",
        f"👤 Người tạo: {name}",
        "⸻",
        f"Nhập ({len(g['inputs'])})"
    ]
    for i in g["inputs"]:
        lines.append(f"{i['time']} | {i['vnd']:,.0f} / {g['rate']} = {i['usdt']:,.2f} USDT")

    lines += ["⸻", f"Xuất ({len(g['outputs'])})"]
    for o in g["outputs"]:
        lines.append(f"-{o['usdt']:,.2f} USDT")

    lines += [
        "⸻",
        f"+ Nhập : {tin:,.2f} USDT",
        f"- Xuất : {tout:,.2f} USDT",
        f"💰 Tổng cộng : <b>{total:,.2f} USDT</b>"
    ]
    return "\n".join(lines)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id, update.effective_chat.id):
        return
    await update.message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_kb()
    )

# ================= CALLBACK =================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    gid = q.message.chat.id

    if not is_admin(uid, gid):
        return

    if gid not in groups:
        groups[gid] = {
            "rate": 38.77,
            "inputs": [],
            "outputs": []
        }

    g = groups[gid]

    if q.data == "admin":
        await q.edit_message_text("👑 ADMIN MENU", reply_markup=admin_menu_kb())

    elif q.data == "add_admin":
        GROUP_ADMINS.setdefault(gid, set()).add(uid)
        await q.answer("Đã thêm admin")

    elif q.data == "remove_admin":
        GROUP_ADMINS.get(gid, set()).discard(uid)
        await q.answer("Đã xóa admin")

    elif q.data == "calc":
        await q.edit_message_text("🧮 Nhập +VND hoặc -USDT")

    elif q.data == "back":
        await q.edit_message_text(MAIN_MENU_TEXT, reply_markup=main_menu_kb())

    elif q.data == "close":
        await q.message.delete()

# ================= MESSAGE =================
async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    gid = update.effective_chat.id

    if not is_admin(uid, gid):
        return

    msg = update.message.text.strip()
    g = groups.setdefault(gid, {"rate": 38.77, "inputs": [], "outputs": []})

    if msg.startswith("+"):
        vnd = float(msg[1:])
        usdt = round(vnd / g["rate"], 2)
        g["inputs"].append({"time": now_time(), "vnd": vnd, "usdt": usdt})
        await update.message.reply_text(render_bill(update.effective_user.first_name, g), parse_mode="HTML")

    elif msg.startswith("-"):
        usdt = float(msg[1:])
        g["outputs"].append({"usdt": usdt})
        await update.message.reply_text(render_bill(update.effective_user.first_name, g), parse_mode="HTML")

# ================= RUN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    print("🐉 TianLong Bot RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
