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
            "❌ Join all channels first",
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
🔍 <b>RESULT FOUND</b>

🌍 Country: {result.get('country')}
📞 Number: <code>{result.get('number')}</code>
🆔 User ID: <code>{result.get('tg_id')}</code>

👨‍💻 Developer: @T4HKR
"""
    await update.message.reply_text(msg, parse_mode="HTML")

# ================= /CHECK =================
async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_type = update.effective_chat.type
    user = get_user(update.effective_user.id)

    # ===== GROUP =====
    if chat_type != "private":

        if update.message.reply_to_message:
            query = str(update.message.reply_to_message.from_user.id)

        elif context.args:
            query = context.args[0]

        else:
            await update.message.reply_text(
                "❌ Use:\nReply + /check\nor\n/check @username\nor\n/check userID"
            )
            return

        await send_result(update, query)
        return

    # ===== PRIVATE =====
    else:
        if not can_search(user):
            await update.message.reply_text("❌ Limit over")
            return

        if update.message.reply_to_message:
            query = str(update.message.reply_to_message.from_user.id)

        elif context.args:
            query = context.args[0]

        else:
            await update.message.reply_text("❌ Use: /check @username or reply")
            return

        await send_result(update, query)

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
        await update.message.reply_text(f"Credits: {user[1]}\nDaily Left: {5-user[2]}")
        return

    if text == "🎁 Refer & Earn":
        await update.message.reply_text(f"https://t.me/{BOT_USERNAME}?start={user_id}")
        return

    if text == "❓ Help":
        await update.message.reply_text("Send username or ID")
        return

    if text == "🚀 Lookup Now":
        context.user_data["lookup"] = True
        await update.message.reply_text("Send @username or userID")
        return

    if context.user_data.get("lookup") and (text.startswith("@") or text.isdigit()):
        context.user_data["lookup"] = False

        if not can_search(user):
            await update.message.reply_text("❌ Limit Over")
            return

        await send_result(update, text)
        return

    if text.startswith("@") or text.isdigit():
        if not can_search(user):
            await update.message.reply_text("❌ Limit Over")
            return
        await send_result(update, text)
        return

    await update.message.reply_text("❌ Invalid")

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("check", check_user))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
