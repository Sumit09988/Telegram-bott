import requests
import json
import time
from datetime import datetime, date
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import *
from database import *

# ================= UI =================
user_keyboard = [
    ["🚀 Lookup Now"],
    ["💰 My Credits", "🎁 Refer & Earn"],
    ["❓ Help"]
]

admin_keyboard = [
    ["👥 Total Users"],
    ["💰 Add Credits"],
    ["📢 Broadcast"]
]

# ================= CHANNEL =================
async def check_join(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name

    if not await check_join(user_id, context.bot):
        await update.message.reply_text(f"❌ Join channel first: {CHANNEL}")
        return

    is_new = not user_exists(user_id)

    ref = None
    if context.args:
        try:
            ref = int(context.args[0])
        except:
            pass

    add_user(user_id, ref)

    if is_new and ref and ref != user_id:
        add_credit(ref)

    if is_new:
        try:
            await context.bot.send_message(ADMIN_ID, f"🆕 New User: {user_id}")
        except:
            pass

    user = get_user(user_id)
    now = datetime.now()

    msg = f"""
💎 <b>WELCOME TO PREMIUM BOT</b>

👤 {name}
🆔 <b>{user_id}</b>

💰 Credits: {user[1]}
📊 Daily Left: {5-user[2]}

📅 {now.strftime("%d-%m-%Y")}
⏰ {now.strftime("%I:%M %p")}
"""

    keyboard = ReplyKeyboardMarkup(
        user_keyboard + admin_keyboard if str(user_id) == str(ADMIN_ID) else user_keyboard,
        resize_keyboard=True
    )

    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)

# ================= LIMIT =================
def can_search(user):
    user_id, credits, daily_used, last_reset, _ = user
    today = str(date.today())

    if last_reset != today:
        cursor.execute("UPDATE users SET daily_used=0, last_reset=? WHERE user_id=?", (today, user_id))
        conn.commit()

    if daily_used < 5:
        cursor.execute("UPDATE users SET daily_used=daily_used+1 WHERE user_id=?", (user_id,))
        conn.commit()
        return True

    elif credits > 0:
        cursor.execute("UPDATE users SET credits=credits-1 WHERE user_id=?", (user_id,))
        conn.commit()
        return True

    return False

# ================= API =================
def fetch_data(url):
    for _ in range(3):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.json()
        except:
            time.sleep(1)
    return None

# 🔥 number extract fix
def extract_number(value):
    if isinstance(value, dict):
        return value.get("number")
    return value

async def send_result(update, query):
    url = f"http://eris-osint.vercel.app/info?key={API_KEY}&id={query}"
    data = fetch_data(url)

    if not data:
        await update.message.reply_text("⚠️ API Error")
        return

    result = data.get("result") or data.get("data") or data

    if isinstance(result, str):
        try:
            result = json.loads(result)
        except:
            pass

    # 🔥 direct extraction
    number = extract_number(result.get("number") or result.get("phone") or result.get("mobile"))
    country = result.get("country") or result.get("Country")
    tg_id = result.get("tg_id") or result.get("id") or result.get("user_id")

    if not number:
        await update.message.reply_text(f"❌ DATA NOT FOUND\nID: {query}")
        return

    msg = f"""
🔍 <b>RESULT FOUND</b>

👤 Username: {query}
🌍 Country: {country or "N/A"}
📞 Number: <code>{number}</code>
🆔 User ID: <b>{tg_id or "N/A"}</b>
"""

    await update.message.reply_text(msg, parse_mode="HTML")

# ================= CHECK =================
async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    if not can_search(user):
        await update.message.reply_text("❌ Limit over")
        return

    if update.message.reply_to_message:
        query = str(update.message.reply_to_message.from_user.id)
    elif context.args:
        query = context.args[0]
    else:
        await update.message.reply_text("❌ Use /check @username")
        return

    await send_result(update, query)

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if not await check_join(user_id, context.bot):
        await update.message.reply_text("❌ Join channel first")
        return

    add_user(user_id)
    user = get_user(user_id)

    if text == "💰 My Credits":
        await update.message.reply_text(f"Credits: {user[1]}\nDaily Left: {5-user[2]}")
        return

    if text == "🎁 Refer & Earn":
        await update.message.reply_text(f"https://t.me/{BOT_USERNAME}?start={user_id}")
        return

    if text == "❓ Help":
        await update.message.reply_text("Send @username or ID")
        return

    if text == "🚀 Lookup Now":
        await update.message.reply_text("Send @username or ID")
        return

    if text.startswith("@") or text.isdigit():
        if not can_search(user):
            await update.message.reply_text("❌ Limit over")
            return
        await send_result(update, text)
        return

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("check", check_user))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🚀 Bot running...")

app.run_polling()
