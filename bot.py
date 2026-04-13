import requests
import json
import time
from datetime import datetime, date
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
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

# ================= CHANNEL CHECK =================
async def check_join(user_id, bot):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================= JOIN BUTTON =================
def join_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel 1", url="https://t.me/SUMITNETW0RK")],
        [InlineKeyboardButton("📢 Join Channel 2", url="https://t.me/lokixnetwork")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name

    if not await check_join(user_id, context.bot):
        await update.message.reply_text(
            "❌ <b>Join all channels first</b>",
            parse_mode="HTML",
            reply_markup=join_buttons()
        )
        return

    add_user(user_id)
    user = get_user(user_id)
    now = datetime.now()

    msg = f"""
💎 <b>WELCOME TO PREMIUM BOT</b> 💎

👤 <b>Name:</b> {name}
🆔 <b>User ID:</b> <code>{user_id}</code>

💰 <b>Credits:</b> {user[1]}

📅 {now.strftime("%Y-%m-%d")}
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
        daily_used = 0

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
    try:
        res = requests.get(url, timeout=10)
        return res.json()
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
        await update.message.reply_text(f"❌ Data not found\nID: {query}")
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

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    text = update.message.text

    if not await check_join(user_id, context.bot):
        await update.message.reply_text(
            "❌ Join all channels first",
            reply_markup=join_buttons()
        )
        return

    add_user(user_id)
    user = get_user(user_id)

    if text == "💰 My Credits":
        await update.message.reply_text(f"Credits: {user[1]}")
        return

    if text == "🎁 Refer & Earn":
        await update.message.reply_text(f"https://t.me/{BOT_USERNAME}?start={user_id}")
        return

    if text == "❓ Help":
        await update.message.reply_text("Send username or ID")
        return

    if text.startswith("@") or text.isdigit():
        if not can_search(user):
            await update.message.reply_text("❌ Limit Over")
            return
        await send_result(update, text)
        return

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
