import os
import sqlite3
from datetime import datetime, timezone, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
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
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN")

SUPER_ADMINS = {8572604188}   # sửa ID của bạn
DB = "bill.db"

# ================= TIME =================
def tz_vn():
    return timezone(timedelta(hours=7))

def now():
    return datetime.now(tz_vn())

def today():
    return now().strftime("%d/%m/%Y")

def now_time():
    return now().strftime("%H:%M")

# ================= DATABASE =================
conn = sqlite3.connect(DB, check_same_thread=False)
cur = conn.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS group_config (
    gid INTEGER PRIMARY KEY,
    rate REAL DEFAULT 1,
    fee REAL DEFAULT 0,
    lang TEXT DEFAULT 'VN'
);

CREATE TABLE IF NOT EXISTS admins (
    gid INTEGER,
    uid INTEGER
);

CREATE TABLE IF NOT EXISTS bill (
    gid INTEGER,
    type TEXT,
    vnd REAL,
    usdt REAL,
    time TEXT
);
""")
conn.commit()

# ================= I18N =================
LANG = {
    "VN": {
        "menu": "📌 MENU",
        "calc": "🧮 Máy tính",
        "admin": "👑 Quản lý Admin",
        "close": "❌ Đóng",
        "back": "⬅️ Quay lại",

        "rate": "🔢 Tỷ giá",
        "fee": "💸 Phí %",
        "in_vnd": "+ Nhập VND",
        "out_usdt": "- Xuất USDT",
        "view_bill": "📄 Xem bill",
        "reset_bill": "♻️ Reset",
        "exit": "⬅️ Thoát",

        "lang_vn": "🇻🇳 VN",
        "lang_cn": "🇨🇳 CN",

        "enter_rate": "Nhập tỷ giá:",
        "enter_fee": "Nhập % phí:",
        "saved": "✅ Đã cập nhật",
        "reset_ok": "♻️ Đã reset bill",

        "bill": "🧾 HÓA ĐƠN",
        "rate_fee": "💱 Tỷ giá: {rate} | Phí: {fee}%",
        "input": "Nhập",
        "output": "Xuất",
        "total": "💰 Tổng cộng",

        "admin_panel": "👑 QUẢN LÝ ADMIN",
        "add_admin": "➕ Thêm Admin (reply)",
        "remove_admin": "➖ Xóa Admin (reply)",
        "need_reply": "⚠️ Vui lòng reply người cần thao tác",
        "added_admin": "✅ Đã thêm admin",
        "removed_admin": "❌ Đã xóa admin",
        "no_permission": "⚠️ Bạn không có quyền"
    },

    "CN": {
        "menu": "📌 菜单",
        "calc": "🧮 计算器",
        "admin": "👑 管理员管理",
        "close": "❌ 关闭",
        "back": "⬅️ 返回",

        "rate": "🔢 汇率",
        "fee": "💸 手续费 %",
        "in_vnd": "+ 输入 VND",
        "out_usdt": "- 支出 USDT",
        "view_bill": "📄 查看账单",
        "reset_bill": "♻️ 重置",
        "exit": "⬅️ 退出",

        "lang_vn": "🇻🇳 越南语",
        "lang_cn": "🇨🇳 中文",

        "enter_rate": "请输入汇率：",
        "enter_fee": "请输入手续费 %：",
        "saved": "✅ 已保存",
        "reset_ok": "♻️ 已重置账单",

        "bill": "🧾 账单",
        "rate_fee": "💱 汇率: {rate} | 手续费: {fee}%",
        "input": "收入",
        "output": "支出",
        "total": "💰 总计",

        "admin_panel": "👑 管理员管理",
        "add_admin": "➕ 添加管理员 (回复)",
        "remove_admin": "➖ 删除管理员 (回复)",
        "need_reply": "⚠️ 请回复需要操作的人",
        "added_admin": "✅ 已添加管理员",
        "removed_admin": "❌ 已删除管理员",
        "no_permission": "⚠️ 没有权限"
    }
}

def get_lang(gid):
    cur.execute("SELECT lang FROM group_config WHERE gid=?", (gid,))
    r = cur.fetchone()
    return r[0] if r else "VN"

def t(gid, key, **kwargs):
    lang = get_lang(gid)
    text = LANG.get(lang, LANG["VN"]).get(key, key)
    return text.format(**kwargs)

# ================= PERMISSION =================
def is_super(uid):
    return uid in SUPER_ADMINS

def is_admin(uid, gid):
    cur.execute("SELECT 1 FROM admins WHERE gid=? AND uid=?", (gid, uid))
    return is_super(uid) or cur.fetchone() is not None

# ================= KEYBOARD =================
def user_menu(gid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(gid,"calc"), callback_data="calc")],
        [InlineKeyboardButton(t(gid,"close"), callback_data="close")]
    ])

def admin_menu(gid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(gid,"calc"), callback_data="calc")],
        [InlineKeyboardButton(t(gid,"admin"), callback_data="admin")],
        [InlineKeyboardButton(t(gid,"close"), callback_data="close")]
    ])

def admin_manage_kb(gid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(gid,"add_admin"), callback_data="add_admin")],
        [InlineKeyboardButton(t(gid,"remove_admin"), callback_data="remove_admin")],
        [InlineKeyboardButton(t(gid,"back"), callback_data="back")]
    ])

def calc_kb(gid):
    return ReplyKeyboardMarkup(
        [
            [t(gid,"rate"), t(gid,"fee")],
            [t(gid,"in_vnd"), t(gid,"out_usdt")],
            [t(gid,"view_bill"), t(gid,"reset_bill")],
            [t(gid,"lang_vn"), t(gid,"lang_cn")],
            [t(gid,"exit")]
        ],
        resize_keyboard=True
    )

# ================= BILL =================
def render_bill(gid, name):
    cur.execute("SELECT rate, fee FROM group_config WHERE gid=?", (gid,))
    rate, fee = cur.fetchone()

    cur.execute("SELECT * FROM bill WHERE gid=?", (gid,))
    rows = cur.fetchall()

    total_in = sum(r[3] for r in rows if r[1] == "IN")
    total_out = sum(r[3] for r in rows if r[1] == "OUT")
    total = total_in - total_out

    lines = [
        f"{t(gid,'bill')} | {today()}",
        f"👤 {name}",
        t(gid,"rate_fee", rate=rate, fee=fee),
        "⸻"
    ]

    for r in rows:
        if r[1] == "IN":
            lines.append(f"{r[4]} | +{r[2]:,.0f} VND → {r[3]:,.2f} USDT")
        else:
            lines.append(f"{r[4]} | -{r[3]:,.2f} USDT")

    lines += [
        "⸻",
        f"+ {t(gid,'input')}: {total_in:,.2f} USDT",
        f"- {t(gid,'output')}: {total_out:,.2f} USDT",
        f"{t(gid,'total')}: <b>{total:,.2f} USDT</b>"
    ]
    return "\n".join(lines)

# ================= START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    gid = update.effective_chat.id

    cur.execute("INSERT OR IGNORE INTO group_config(gid) VALUES (?)", (gid,))
    conn.commit()

    kb = admin_menu(gid) if is_admin(uid, gid) else user_menu(gid)
    await update.message.reply_text(t(gid,"menu"), reply_markup=kb)

# ================= CALLBACK =================
async def cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    gid = q.message.chat.id
    uid = q.from_user.id

    if q.data == "calc":
        await q.message.reply_text(t(gid,"calc"), reply_markup=calc_kb(gid))

    elif q.data == "admin":
        if not is_admin(uid, gid):
            await q.answer(t(gid,"no_permission"), show_alert=True)
            return
        await q.edit_message_text(t(gid,"admin_panel"), reply_markup=admin_manage_kb(gid))

    elif q.data == "add_admin":
        if not q.message.reply_to_message:
            await q.answer(t(gid,"need_reply"), show_alert=True)
            return
        target = q.message.reply_to_message.from_user.id
        cur.execute("INSERT INTO admins VALUES (?,?)", (gid, target))
        conn.commit()
        await q.answer(t(gid,"added_admin"))

    elif q.data == "remove_admin":
        if not q.message.reply_to_message:
            await q.answer(t(gid,"need_reply"), show_alert=True)
            return
        target = q.message.reply_to_message.from_user.id
        cur.execute("DELETE FROM admins WHERE gid=? AND uid=?", (gid, target))
        conn.commit()
        await q.answer(t(gid,"removed_admin"))

    elif q.data == "back":
        await q.edit_message_text(t(gid,"menu"), reply_markup=admin_menu(gid))

    elif q.data == "close":
        await q.delete_message()

# ================= MESSAGE =================
async def msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    gid = update.effective_chat.id
    uid = update.effective_user.id
    name = update.effective_user.first_name

    if text == t(gid,"exit"):
        kb = admin_menu(gid) if is_admin(uid, gid) else user_menu(gid)
        await update.message.reply_text(t(gid,"menu"), reply_markup=kb)
        return

    if text == t(gid,"lang_vn"):
        cur.execute("UPDATE group_config SET lang='VN' WHERE gid=?", (gid,))
        conn.commit()
        await update.message.reply_text(t(gid,"menu"), reply_markup=calc_kb(gid))
        return

    if text == t(gid,"lang_cn"):
        cur.execute("UPDATE group_config SET lang='CN' WHERE gid=?", (gid,))
        conn.commit()
        await update.message.reply_text(t(gid,"menu"), reply_markup=calc_kb(gid))
        return

    if text == t(gid,"rate"):
        ctx.user_data["set_rate"] = True
        await update.message.reply_text(t(gid,"enter_rate"))
        return

    if ctx.user_data.get("set_rate"):
        cur.execute("UPDATE group_config SET rate=? WHERE gid=?", (float(text), gid))
        conn.commit()
        ctx.user_data.clear()
        await update.message.reply_text(t(gid,"saved"))
        return

    if text == t(gid,"fee"):
        ctx.user_data["set_fee"] = True
        await update.message.reply_text(t(gid,"enter_fee"))
        return

    if ctx.user_data.get("set_fee"):
        cur.execute("UPDATE group_config SET fee=? WHERE gid=?", (float(text), gid))
        conn.commit()
        ctx.user_data.clear()
        await update.message.reply_text(t(gid,"saved"))
        return

    if text.startswith("+"):
        vnd = float(text[1:])
        cur.execute("SELECT rate, fee FROM group_config WHERE gid=?", (gid,))
        rate, fee = cur.fetchone()
        usdt = (vnd / rate) * (1 - fee / 100)
        cur.execute("INSERT INTO bill VALUES (?,?,?,?,?)",
                    (gid, "IN", vnd, round(usdt,2), now_time()))
        conn.commit()
        await update.message.reply_text(render_bill(gid,name), parse_mode="HTML")

    if text.startswith("-"):
        usdt = float(text[1:])
        cur.execute("INSERT INTO bill VALUES (?,?,?,?,?)",
                    (gid, "OUT", 0, usdt, now_time()))
        conn.commit()
        await update.message.reply_text(render_bill(gid,name), parse_mode="HTML")

    if text == t(gid,"view_bill"):
        await update.message.reply_text(render_bill(gid,name), parse_mode="HTML")

    if text == t(gid,"reset_bill"):
        cur.execute("DELETE FROM bill WHERE gid=?", (gid,))
        conn.commit()
        await update.message.reply_text(t(gid,"reset_ok"))

# ================= RUN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))
    print("🐉 TIANLONG BILL BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
