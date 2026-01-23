import os
from datetime import datetime, timezone, timedelta
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

# ================== CONFIG ==================
BOT_TOKEN = "7993054192:AAEMYvFa_WG-_XuT4RkeW_qUNtVO-P-vy_c"
OWNER_ID = 8572604188  # 👈 ID chủ bot

ADMINS = {OWNER_ID}
GROUP_ADMINS = {}

groups = {}

# ================== TIME ==================
def tz_vn():
    return timezone(timedelta(hours=7))

def today():
    return datetime.now(tz_vn()).strftime("%d/%m/%Y")

def now_time():
    return datetime.now(tz_vn()).strftime("%H:%M")

# ================== MENUS ==================
MAIN_MENU = ReplyKeyboardMarkup(
    [
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

# ================== HELPERS ==================
def is_admin(uid, gid):
    return uid == OWNER_ID or uid in GROUP_ADMINS.get(gid, set())

def reset_state(context):
    context.user_data.clear()

# ================== BILL (KHÔNG ĐỤNG) ==================
def render_bill(name, g):
    total_in = sum(i["usdt"] for i in g["inputs"])
    total_out = sum(o["usdt"] for o in g["outputs"])
    total = total_in - total_out

    if g["lang"] == "CN":
        lines = [
            f"🧾 账单 | {today()}",
            f"👤 创建者: {name}",
            "⸻",
            f"收入 ({len(g['inputs'])})"
        ]
        for i in g["inputs"]:
            lines.append(f"{i['time']} | {i['vnd']:,.0f} / {g['rate']} = {i['usdt']:,.2f} USDT")

        lines += ["⸻", f"支出 ({len(g['outputs'])})"]
        for o in g["outputs"]:
            lines.append(f"-{o['usdt']:,.2f} USDT")

        lines += [
            "⸻",
            f"+ 收入 : {total_in:,.2f} USDT",
            f"- 支出 : {total_out:,.2f} USDT",
            f"💰 总计 : <b>{total:,.2f} USDT</b>"
        ]
        return "\n".join(lines)

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
        f"+ Nhập : {total_in:,.2f} USDT",
        f"- Xuất : {total_out:,.2f} USDT",
        f"💰 Tổng cộng : <b>{total:,.2f} USDT</b>"
    ]
    return "\n".join(lines)

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMINS:
        return
    await update.message.reply_text("📌 MENU CHÍNH", reply_markup=MAIN_MENU)

# ================== HANDLER ==================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    uid = update.effective_user.id
    gid = update.effective_chat.id
    name = update.effective_user.first_name

    if uid not in ADMINS:
        return

    if gid not in groups:
        groups[gid] = {
            "rate": 1.0,
            "fee": 0.0,
            "lang": "VN",
            "inputs": [],
            "outputs": []
        }

    g = groups[gid]

    # ===== MENU =====
    if msg == "🧮 Máy tính":
        await update.message.reply_text("🧮 Máy tính", reply_markup=CALC_MENU)
        return

    if msg == "👑 Admin":
        if uid != OWNER_ID:
            return
        await update.message.reply_text("👑 ADMIN", reply_markup=ADMIN_MENU)
        return

    if msg == "⬅️ Quay lại":
        await update.message.reply_text("📌 MENU CHÍNH", reply_markup=MAIN_MENU)
        return

    if msg == "❌ Đóng":
        reset_state(context)
        await update.message.reply_text("Đã đóng", reply_markup=None)
        return

    # ===== LANGUAGE =====
    if msg.startswith("VN"):
        g["lang"] = "VN"
        await update.message.reply_text("Đã chuyển Tiếng Việt")
        return

    if msg.startswith("CN"):
        g["lang"] = "CN"
        await update.message.reply_text("已切换中文")
        return

    # ===== RATE =====
    if msg == "🔢 Tỷ giá":
        context.user_data["set_rate"] = True
        await update.message.reply_text("Nhập tỷ giá:")
        return

    if context.user_data.get("set_rate"):
        try:
            rate = float(msg)
            if rate <= 0:
                raise ValueError
            g["rate"] = rate
            reset_state(context)
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
            fee = float(msg)
            if fee < 0:
                raise ValueError
            g["fee"] = fee
            reset_state(context)
            await update.message.reply_text("✅ Đã đặt phí")
        except:
            await update.message.reply_text("❌ Phí không hợp lệ")
        return

    # ===== RESET BILL =====
    if msg in ["+0", "-0"]:
        g["inputs"].clear()
        g["outputs"].clear()
        await update.message.reply_text(render_bill(name, g), parse_mode="HTML")
        return

    # ===== INPUT =====
    if msg.startswith("+"):
        try:
            vnd = float(msg[1:])
            usdt = round(vnd / g["rate"], 2)
            g["inputs"].append({"time": now_time(), "vnd": vnd, "usdt": usdt})
            await update.message.reply_text(render_bill(name, g), parse_mode="HTML")
        except:
            pass
        return

    # ===== OUTPUT =====
    if msg.startswith("-"):
        try:
            usdt = round(float(msg[1:]), 2)
            if usdt > 0:
                g["outputs"].append({"usdt": usdt})
            await update.message.reply_text(render_bill(name, g), parse_mode="HTML")
        except:
            pass
        return

# ================== ADMIN ==================
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    uid = update.effective_user.id
    gid = update.effective_chat.id

    if uid != OWNER_ID:
        return

    if msg == "➕ Thêm Admin":
        context.user_data["add_admin"] = True
        await update.message.reply_text("Nhập ID admin:")
        return

    if context.user_data.get("add_admin"):
        try:
            aid = int(msg)
            GROUP_ADMINS.setdefault(gid, set()).add(aid)
            ADMINS.add(aid)
            context.user_data.clear()
            await update.message.reply_text("✅ Đã thêm admin")
        except:
            await update.message.reply_text("❌ ID không hợp lệ")
        return

    if msg == "➖ Xóa Admin":
        context.user_data["remove_admin"] = True
        await update.message.reply_text("Nhập ID admin cần xóa:")
        return

    if context.user_data.get("remove_admin"):
        try:
            aid = int(msg)
            GROUP_ADMINS.get(gid, set()).discard(aid)
            ADMINS.discard(aid)
            context.user_data.clear()
            await update.message.reply_text("✅ Đã xóa admin")
        except:
            await update.message.reply_text("❌ ID không hợp lệ")
        return

    if msg == "📋 Danh sách Admin":
        admins = GROUP_ADMINS.get(gid, set())
        text = "📋 ADMIN LIST\n" + ("\n".join(map(str, admins)) if admins else "Chưa có admin")
        await update.message.reply_text(text)
        return

# ================== RUN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    print("🐉 TianLong Bot RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
