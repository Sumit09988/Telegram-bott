import requests
import json
import time
from datetime import date
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import *
from database import *

# MENU
keyboard = [
    ["🔍 Lookup via Chat"],
    ["🎁 Refer & Earn", "📊 My Credits"]
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# CHANNEL CHECK
async def check_join(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# CHECK USER EXISTS
def user_exists(user_id):
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

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

    # ✅ refer reward only new user
    if is_new and ref and ref != user_id:
        add_credit(ref)

    # 🔔 admin alert
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"🆕 New User Started Bot\n\n👤 ID: {user_id}"
        )
    except:
        pass

    await update.message.reply_text("🔥 Welcome Premium Bot", reply_markup=markup)

# LIMIT SYSTEM
def can_search(user):
    user_id, credits, daily_used, last_reset, _ = user
    today = str(date.today())

    if last_reset != today:
        cursor.execute("UPDATE users SET daily_used=0, last_reset=? WHERE user_id=?", (today, user_id))
        conn.commit()
        daily_used = 0

    if daily_used < 5:
        cursor.execute("UPDATE users SET daily_used = daily_used + 1 WHERE user_id=?", (user_id,))
        conn.commit()
        return True

    elif credits > 0:
        cursor.execute("UPDATE users SET credits = credits - 1 WHERE user_id=?", (user_id,))
        conn.commit()
        return True

    return False

# API FETCH
def fetch_data(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    for _ in range(3):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return res.json()
        except:
            time.sleep(1)
    return None

# /CHECK COMMAND
async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not can_search(user):
        await update.message.reply_text("❌ Limit over")
        return

    # QUERY DETECT
    if update.message.reply_to_message:
        query = str(update.message.reply_to_message.from_user.id)

    elif context.args:
        text = context.args[0]

        if text.startswith("@"):
            query = text
        elif text.isdigit():
            query = text
        else:
            await update.message.reply_text("❌ Invalid input")
            return

    else:
        await update.message.reply_text(
            "❌ Use:\n\n👉 /check @username\n👉 /check userID\n👉 reply + /check"
        )
        return

    url = f"http://eris-osint.vercel.app/info?key={API_KEY}&id={query}"
    data = fetch_data(url)

    if not data:
        await update.message.reply_text("⚠️ API Error")
        return

    result_raw = data.get("result")

    if not result_raw:
        await update.message.reply_text(
            f"<b>❌ DATA NOT FOUND</b>\n\n🆔 <code>{query}</code>",
            parse_mode="HTML"
        )
        return

    try:
        result = json.loads(result_raw) if isinstance(result_raw, str) else result_raw
    except:
        await update.message.reply_text("⚠️ Parse error")
        return

    if not result.get("number"):
        await update.message.reply_text(
            f"<b>❌ DATA NOT FOUND</b>\n\n🆔 <code>{query}</code>",
            parse_mode="HTML"
        )
        return

    msg = f"""
<b>🔍 RESULT FOUND</b>

━━━━━━━━━━━━━━

🌍 <b>Country:</b> {result.get('country')}
📞 <b>Number:</b> <code>{result.get('number')}</code>
🆔 <b>User ID:</b> <code>{result.get('tg_id')}</code>

━━━━━━━━━━━━━━
👨‍💻 <b>DEVELOPER:</b> @T4HKR
"""

    await update.message.reply_text(msg, parse_mode="HTML")

# HANDLE (PRIVATE ONLY)
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id

    if not await check_join(user_id, context.bot):
        await update.message.reply_text(f"❌ Join channel first: {CHANNEL}")
        return

    add_user(user_id)
    user = get_user(user_id)
    text = update.message.text

    if text == "📊 My Credits":
        await update.message.reply_text(
            f"""📊 <b>Your Stats</b>

🎯 Daily Free Left: {5 - user[2]}
💰 Credits: {user[1]}""",
            parse_mode="HTML"
        )

    elif text == "🎁 Refer & Earn":
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        await update.message.reply_text(link)

    elif text == "🔍 Lookup via Chat":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👉 Open Private", url=f"https://t.me/{BOT_USERNAME}")]
        ])
        await update.message.reply_text("📩 Open private & use /check", reply_markup=kb)

# RUN
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("check", check_user))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
