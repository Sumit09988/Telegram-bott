import requests
import json
from datetime import date
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import *
from database import *

# 🎛️ MENU
keyboard = [
    ["🔍 Lookup via Chat"],
    ["🎁 Refer & Earn", "📊 My Credits"]
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# 🔐 CHANNEL CHECK
async def check_join(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# 🚀 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await check_join(user_id, context.bot):
        await update.message.reply_text(f"❌ Join channel first: {CHANNEL}")
        return

    ref = None
    if context.args:
        try:
            ref = int(context.args[0])
        except:
            pass

    add_user(user_id, ref)

    if ref and ref != user_id:
        add_credit(ref)

    await update.message.reply_text("🔥 Welcome to Premium Lookup Bot", reply_markup=markup)

# 🔄 LIMIT SYSTEM
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

# 📢 BROADCAST
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = " ".join(context.args)
    users = get_all_users()

    for u in users:
        try:
            await context.bot.send_message(u[0], msg)
        except:
            pass

    await update.message.reply_text("✅ Broadcast sent")

# 💰 ADD CREDITS
async def addcredits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        uid = int(context.args[0])
        amt = int(context.args[1])

        cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amt, uid))
        conn.commit()

        await update.message.reply_text(f"✅ Added {amt} credits")
    except:
        await update.message.reply_text("Usage: /addcredits user_id amount")

# 🧠 MAIN HANDLE
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await check_join(user_id, context.bot):
        await update.message.reply_text(f"❌ Join channel first: {CHANNEL}")
        return

    add_user(user_id)
    user = get_user(user_id)
    text = update.message.text

    # 📊 Credits
    if text == "📊 My Credits":
        await update.message.reply_text(
            f"📊 <b>Your Stats</b>\n\n💰 Credits: {user[1]}\n📅 Used: {user[2]}/5",
            parse_mode="HTML"
        )
        return

    # 🎁 Refer
    if text == "🎁 Refer & Earn":
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        await update.message.reply_text(
            f"🎁 <b>Refer & Earn</b>\n\nInvite Link:\n{link}",
            parse_mode="HTML"
        )
        return

    # 🔍 Lookup Button
    if text == "🔍 Lookup via Chat":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👉 Open Private", url=f"https://t.me/{BOT_USERNAME}")]
        ])
        await update.message.reply_text(
            "📩 Private me open karo & user ka message forward/reply karo",
            reply_markup=kb
        )
        return

    # 🎯 QUERY DETECT
    if update.message.reply_to_message:
        query = str(update.message.reply_to_message.from_user.id)

    elif update.message.forward_from:
        query = str(update.message.forward_from.id)

    elif text.startswith("@"):
        query = text.replace("@", "")

    elif text.isdigit():
        query = text

    else:
        await update.message.reply_text(
            "❌ Use:\n\n👉 @username\n👉 userID\n👉 reply/forward"
        )
        return

    # 🔐 LIMIT
    if not can_search(user):
        await update.message.reply_text("❌ Limit over. Refer to earn.")
        return

    # 🌐 API CALL
    url = f"http://eris-osint.vercel.app/info?key={API_KEY}&id={query}"

    try:
        res = requests.get(url)
        data = res.json()

        if data.get("success") == False:
            await update.message.reply_text("❌ Data not found")
            return

        result = json.loads(data.get("result", "{}"))

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

    except:
        await update.message.reply_text("⚠️ API Error")

# 🚀 RUN
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("addcredits", addcredits))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
