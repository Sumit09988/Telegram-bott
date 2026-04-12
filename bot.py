import requests
import json
import time
from datetime import datetime, date
from telegram import Update, ReplyKeyboardMarkup, MessageEntity
from telegram.constants import MessageEntityType
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import *
from database import *

# 🔥 PREMIUM EMOJI IDS
EMOJIS = [
    "6147902731085420231",
    "6235717714023814969",
    "6235234190900598910",
    "6235475653961979149",
    "6113743365826677162"
]

# UI
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

# JOIN CHECK
async def check_join(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def user_exists(user_id):
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name

    if not await check_join(user_id, context.bot):
        await update.message.reply_text(f"❌ Join channel first: {CHANNEL}")
        return

    is_new = not user_exists(user_id)
    add_user(user_id)

    if is_new:
        await context.bot.send_message(ADMIN_ID, f"🆕 New User\nID: {user_id}")

    user = get_user(user_id)
    now = datetime.now()

    text = "💎💎💎 PREMIUM BOT 💎💎💎"

    entities = [
        MessageEntity(type=MessageEntityType.CUSTOM_EMOJI, offset=0, length=1, custom_emoji_id=EMOJIS[0]),
        MessageEntity(type=MessageEntityType.CUSTOM_EMOJI, offset=1, length=1, custom_emoji_id=EMOJIS[1]),
        MessageEntity(type=MessageEntityType.CUSTOM_EMOJI, offset=2, length=1, custom_emoji_id=EMOJIS[2]),
    ]

    await update.message.reply_text(text, entities=entities)

    msg = f"""
👤 Name: {name}
🆔 ID: {user_id}

💰 Credits: {user[1]}
📅 Date: {now.strftime("%Y-%m-%d")}
⏰ Time: {now.strftime("%I:%M %p")}
"""

    if str(user_id) == str(ADMIN_ID):
        kb = ReplyKeyboardMarkup(user_keyboard + admin_keyboard, resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(user_keyboard, resize_keyboard=True)

    await update.message.reply_text(msg, reply_markup=kb)

# LIMIT
def can_search(user):
    user_id, credits, used, last, _ = user
    today = str(date.today())

    if last != today:
        cursor.execute("UPDATE users SET daily_used=0, last_reset=? WHERE user_id=?", (today, user_id))
        conn.commit()
        used = 0

    if used < 5:
        cursor.execute("UPDATE users SET daily_used=daily_used+1 WHERE user_id=?", (user_id,))
        conn.commit()
        return True
    elif credits > 0:
        cursor.execute("UPDATE users SET credits=credits-1 WHERE user_id=?", (user_id,))
        conn.commit()
        return True
    return False

# API
def fetch_data(url):
    try:
        r = requests.get(url, timeout=10)
        return r.json()
    except:
        return None

async def send_result(update, query):
    url = f"http://eris-osint.vercel.app/info?key={API_KEY}&id={query}"
    data = fetch_data(url)

    if not data:
        await update.message.reply_text("⚠️ API Error")
        return

    result_raw = data.get("result")

    if not result_raw:
        await update.message.reply_text(f"❌ Not Found\nID: {query}")
        return

    try:
        result = json.loads(result_raw) if isinstance(result_raw, str) else result_raw
    except:
        await update.message.reply_text("⚠️ Parse Error")
        return

    msg = f"""
🔍 RESULT

🌍 {result.get('country')}
📞 {result.get('number')}
🆔 {result.get('tg_id')}

👨‍💻 @T4HKR
"""
    await update.message.reply_text(msg)

# /check
async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    if not can_search(user):
        await update.message.reply_text("❌ Limit Over")
        return

    if update.message.reply_to_message:
        q = str(update.message.reply_to_message.from_user.id)
    elif context.args:
        q = context.args[0]
    else:
        await update.message.reply_text("❌ Use /check @username")
        return

    await send_result(update, q)

# HANDLE
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    add_user(user_id)
    user = get_user(user_id)

    if text == "💰 My Credits":
        await update.message.reply_text(f"Credits: {user[1]}")
        return

    if text == "🎁 Refer & Earn":
        await update.message.reply_text(f"https://t.me/{BOT_USERNAME}?start={user_id}")
        return

    if text == "❓ Help":
        await update.message.reply_text("Send @username or ID\nGroup: /check")
        return

    if text.startswith("@") or text.isdigit():
        if not can_search(user):
            await update.message.reply_text("❌ Limit Over")
            return
        await send_result(update, text)
        return

# RUN
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("check", check_user))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
