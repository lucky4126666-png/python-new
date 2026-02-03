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
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"

SUPER_ADMINS = {5493266423}
GROUP_ADMINS = {}          # {gid: set(uid)}
groups = {}                # data theo chat

# ================= TIME =================
def tz_vn():
    return timezone(timedelta(hours=7))

def today():
    return datetime.now(tz_vn()).strftime("%d/%m/%Y")

def now_time():
    return datetime.now(tz_vn()).strftime("%H:%M")

# ================= PERMISSION =================
def is_admin(uid, gid):
    return uid in SUPER_ADMINS or uid in GROUP_ADMINS.get(gid, set())

# ================= LANGUAGE =================
LANG = {
    "VN": {
        "menu": "📌 MENU MÁY TÍNH",
        "rate": "🔢 Tỷ giá",
        "fee": "💸 Phí %",
        "bill": "📄 Xem bill",
        "reset": "♻ Reset",
        "admin": "👑 Phân quyền",
        "exit": "❌ Thoát",
        "creator": "Người tạo",
        "input": "Nhập",
        "output": "Xuất",
        "total": "Tổng cộng",
        "set_rate": "Nhập tỷ giá:",
        "set_fee": "Nhập % phí:"
    },
    "CN": {
        "menu": "📌 计算菜单",
        "rate": "🔢 汇率",
        "fee": "💸 手续费 %",
        "bill": "📄 查看账单",
        "reset": "♻ 重置",
        "admin": "👑 权限",
        "exit": "❌ 关闭",
        "creator": "创建者",
        "input": "收入",
        "output": "支出",
        "total": "总计",
        "set_rate": "输入汇率：",
        "set_fee": "输入手续费 %："
    }
}

def t(g, key):
    return LANG[g["lang"]][key]

# ================= KEYBOARD =================
def main_menu(g):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(g,"rate"), callback_data="rate"),
         InlineKeyboardButton(t(g,"fee"), callback_data="fee")],
        [InlineKeyboardButton(t(g,"bill"), callback_data="bill"),
         InlineKeyboardButton(t(g,"reset"), callback_data="reset")],
        [InlineKeyboardButton("🇻🇳 VN", callback_data="lang_vn"),
         InlineKeyboardButton("🇨🇳 CN", callback_data="lang_cn")],
        [InlineKeyboardButton(t(g,"admin"), callback_data="admin")],
        [InlineKeyboardButton(t(g,"exit"), callback_data="exit")]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Admin", callback_data="add_admin"),
         InlineKeyboardButton("➖ Remove Admin", callback_data="remove_admin")],
        [InlineKeyboardButton("📋 List Admin", callback_data="list_admin")]
    ])

# ================= BILL =================
def render_bill(g, name):
    total_in = sum(i["usdt"] for i in g["inputs"])
    total_out = sum(o["usdt"] for o in g["outputs"])

    fee_usdt = round(total_in * g["fee"] / 100, 2)
    total = total_in - fee_usdt - total_out

    lines = [
        f"🧾 HÓA ĐƠN | {today()}",
        f"👤 {t(g,'creator')}: {name}",
        "⸻",
        f"{t(g,'input')} ({len(g['inputs'])})"
    ]

    for i in g["inputs"]:
        lines.append(
            f"{i['time']} | {i['vnd']:,.0f} / {i['rate']} = {i['usdt']:,.2f} USDT"
        )

    lines += ["⸻", f"{t(g,'output')} ({len(g['outputs'])})"]

    for o in g["outputs"]:
        lines.append(f"-{o['usdt']:,.2f} USDT")

    lines.append("⸻")
    lines.append(f"+ {t(g,'input')} : {total_in:,.2f} USDT")

    if g["fee"] > 0:
        lines.append(f"💸 Phí nhập ({g['fee']}%) : {fee_usdt:,.2f} USDT")

    lines.append(f"- {t(g,'output')} : {total_out:,.2f} USDT")
    lines.append(f"💰 {t(g,'total')} : <b>{total:,.2f} USDT</b>")

    return "\n".join(lines)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    gid = update.effective_chat.id

    if not is_admin(uid, gid):
        return

    groups.setdefault(gid, {
        "rate": 1.0,
        "fee": 0.0,
        "lang": "VN",
        "inputs": [],
        "outputs": []
    })

    await update.message.reply_text(
        t(groups[gid],"menu"),
        reply_markup=main_menu(groups[gid])
    )

# ================= CALLBACK =================
async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    gid = q.message.chat.id

    if not is_admin(uid, gid):
        return

    g = groups.setdefault(gid, {
        "rate": 1.0,
        "fee": 0.0,
        "lang": "VN",
        "inputs": [],
        "outputs": []
    })

    if q.data == "rate":
        context.user_data["set_rate"] = True
        await q.message.reply_text(t(g,"set_rate"))

    elif q.data == "fee":
        context.user_data["set_fee"] = True
        await q.message.reply_text(t(g,"set_fee"))

    elif q.data == "bill":
        await q.message.reply_text(
            render_bill(g, q.from_user.first_name),
            parse_mode="HTML"
        )

    elif q.data == "reset":
        g["inputs"].clear()
        g["outputs"].clear()
        await q.message.reply_text("✅ Reset xong")

    elif q.data == "lang_vn":
        g["lang"] = "VN"
        await q.message.reply_text("🇻🇳 Tiếng Việt")

    elif q.data == "lang_cn":
        g["lang"] = "CN"
        await q.message.reply_text("🇨🇳 中文")

    elif q.data == "admin":
        await q.message.reply_text("👑 ADMIN", reply_markup=admin_menu())

    elif q.data == "add_admin":
        if not q.message.reply_to_message:
            await q.answer("Reply người cần cấp quyền", show_alert=True)
            return
        target = q.message.reply_to_message.from_user.id
        GROUP_ADMINS.setdefault(gid, set()).add(target)
        await q.message.reply_text("✅ Đã thêm admin")

    elif q.data == "remove_admin":
        if not q.message.reply_to_message:
            await q.answer("Reply admin cần xóa", show_alert=True)
            return
        target = q.message.reply_to_message.from_user.id
        GROUP_ADMINS.get(gid, set()).discard(target)
        await q.message.reply_text("❌ Đã xóa admin")

    elif q.data == "list_admin":
        admins = GROUP_ADMINS.get(gid, set())
        txt = "👑 ADMIN LIST\n"
        txt += "\n".join(str(i) for i in admins) if admins else "Chưa có"
        await q.message.reply_text(txt)

    elif q.data == "exit":
        await q.message.delete()

# ================= MESSAGE =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    uid = update.effective_user.id
    gid = update.effective_chat.id
    name = update.effective_user.first_name

    if not is_admin(uid, gid):
        return

    g = groups.setdefault(gid, {
        "rate": 1.0,
        "fee": 0.0,
        "lang": "VN",
        "inputs": [],
        "outputs": []
    })

    if context.user_data.get("set_rate"):
        g["rate"] = float(msg)
        context.user_data.clear()
        await update.message.reply_text("✅ OK")
        return

    if context.user_data.get("set_fee"):
        g["fee"] = float(msg)
        context.user_data.clear()
        await update.message.reply_text("✅ OK")
        return

    if msg.startswith("+"):
        vnd = float(msg[1:])
        usdt = round(vnd / g["rate"], 2)
        g["inputs"].append({
            "time": now_time(),
            "vnd": vnd,
            "rate": g["rate"],
            "usdt": usdt
        })
        await update.message.reply_text(
            render_bill(g, name),
            parse_mode="HTML"
        )

    elif msg.startswith("-"):
        usdt = round(float(msg[1:]), 2)
        g["outputs"].append({"usdt": usdt})
        await update.message.reply_text(
            render_bill(g, name),
            parse_mode="HTML"
        )

# ================= RUN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    print("🐉 Bot Bill Calculator Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
