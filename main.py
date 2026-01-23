from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from datetime import datetime
import pytz
import re

BOT_TOKEN = "YOUR_BOT_TOKEN"

TZ_VN = pytz.timezone("Asia/Ho_Chi_Minh")

# ====== DATA ======
group_data = {}

def get_group(chat_id):
    if chat_id not in group_data:
        group_data[chat_id] = {
            "rate": None,
            "lang": "VN",
            "logs": [],
            "income": 0.0,
            "expense": 0.0
        }
    return group_data[chat_id]

# ====== FORMAT BILL ======
def render_bill(chat_id, user):
    g = group_data[chat_id]
    now = datetime.now(TZ_VN).strftime("%d/%m/%Y – %H:%M")

    if g["lang"] == "CN":
        header = f"""🧾 账单

👤 创建者: {user}
🕒 时间: {now}

⸻⸻⸻⸻⸻
"""
        empty = "📭 尚未发生任何交易\n"
        footer = f"""
⸻⸻⸻⸻⸻
📥 总收入: {g['income']} USDT
📤 总支出: {g['expense']} USDT
💰 余额: **{g['income'] - g['expense']} USDT**
"""
    else:
        header = f"""🧾 HÓA ĐƠN

👤 Người tạo: {user}
🕒 Thời gian: {now}

⸻⸻⸻⸻⸻
"""
        empty = "📭 Chưa có giao dịch nào được thực hiện\n"
        footer = f"""
⸻⸻⸻⸻⸻
📥 Tổng thu: {g['income']} USDT
📤 Tổng chi: {g['expense']} USDT
💰 Số dư: **{g['income'] - g['expense']} USDT**
"""

    body = ""
    if not g["logs"]:
        body = empty
    else:
        body = "\n".join(g["logs"]) + "\n"

    return header + body + footer

# ====== MESSAGE HANDLER ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user.first_name
    text = update.message.text.strip()

    g = get_group(chat_id)

    # ---- SET RATE ----
    if re.fullmatch(r"\d+(\.\d+)?", text):
        g["rate"] = float(text)
        await update.message.reply_text(
            "✅ Đã đặt tỷ giá" if g["lang"] == "VN" else "✅ 已设置汇率"
        )
        return

    # ---- RESET ----
    if text in ["+0", "-0"]:
        g["logs"].clear()
        g["income"] = 0
        g["expense"] = 0
        await update.message.reply_text(render_bill(chat_id, user))
        return

    # ---- PLUS ----
    if text.startswith("+"):
        if g["rate"] is None:
            await update.message.reply_text(
                "⚠️ Chưa đặt tỷ giá" if g["lang"] == "VN" else "⚠️ 尚未设置汇率"
            )
            return

        vnd = float(text[1:])
        usdt = round(vnd / g["rate"], 2)
        time = datetime.now(TZ_VN).strftime("%H:%M")

        g["income"] += usdt
        g["logs"].append(f"• {time}  {vnd} / {g['rate']} = {usdt} USDT")

        await update.message.reply_text(render_bill(chat_id, user))
        return

    # ---- MINUS ----
    if text.startswith("-"):
        usdt = abs(float(text))
        time = datetime.now(TZ_VN).strftime("%H:%M")

        g["expense"] += usdt
        g["logs"].append(f"• {time}  -{usdt} USDT")

        await update.message.reply_text(render_bill(chat_id, user))
        return

# ====== COMMANDS ======
async def set_lang_vn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_group(update.effective_chat.id)["lang"] = "VN"
    await update.message.reply_text("🇻🇳 Đã chuyển tiếng Việt")

async def set_lang_cn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_group(update.effective_chat.id)["lang"] = "CN"
    await update.message.reply_text("🇨🇳 已切换中文")

# ====== RUN ======
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("vn", set_lang_vn))
app.add_handler(CommandHandler("cn", set_lang_cn))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 BOT RUNNING...")
app.run_polling()
