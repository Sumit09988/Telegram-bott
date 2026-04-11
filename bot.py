import requests
from datetime import date
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import *
from database import *

keyboard = [
    ["🔍 Lookup via Chat"],
    ["🎁 Refer & Earn"],
    ["📊 My Credits"]
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def check_join(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

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

    await update.message.reply_text("Welcome 🚀", reply_markup=markup)

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

async def addcredits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])

        cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amount, user_id))
        conn.commit()

        await update.message.reply_text(f"✅ {amount} credits added")
    except:
        await update.message.reply_text("Usage: /addcredits user_id amount")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await check_join(user_id, context.bot):
        await update.message.reply_text(f"❌ Join channel first: {CHANNEL}")
        return

    add_user(user_id)
    user = get_user(user_id)

    text = update.message.text

    if text == "📊 My Credits":
        await update.message.reply_text(f"💰 Credits: {user[1]}\n📅 Used: {user[2]}/5")
        return

    if text == "🎁 Refer & Earn":
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        await update.message.reply_text(f"Invite link:\n{link}")
        return

    if text == "🔍 Lookup via Chat":
        await update.message.reply_text("Send username or reply in group")
        return

    if update.message.reply_to_message:
        query = str(update.message.reply_to_message.from_user.id)
    else:
        query = text.replace("@", "")

    if can_search(user):
        url = f"http://eris-osint.vercel.app/info?key={API_KEY}&id={query}"
        try:
            res = requests.get(url)
            data = res.json()
            await update.message.reply_text(
                f"🔍 Result:\n{data}\n\n━━━━━━━━━━━━━━\n👨‍💻 DEVELOPER: @T4HKR"
            )
        except:
            await update.message.reply_text("⚠️ API Error")
    else:
        await update.message.reply_text("❌ Limit over. Refer more")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("addcredits", addcredits))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
