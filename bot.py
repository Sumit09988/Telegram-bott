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

# ================= JOIN CHECK =================
async def check_join(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def user_exists(user_id):
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

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

    # 🎁 REFER CREDIT + MESSAGE
    if is_new and ref and ref != user_id:
        cursor.execute("UPDATE users SET credits = credits + 2 WHERE user_id=?", (ref,))
        conn.commit()

        try:
            await context.bot.send_message(
                ref,
                f"🎉 <b>New Referral Joined!</b>\n\n🆔 User ID: <code>{user_id}</code>\n💰 +2 Credits Added",
                parse_mode="HTML"
            )
        except:
            pass

    # 🆕 ADMIN ALERT
    if is_new:
        try:
            await context.bot.send_message(ADMIN_ID, f"🆕 New User\nID: {user_id}")
        except:
            pass

    user = get_user(user_id)
    now = datetime.now()

    msg = f"""
💎 <b>WELCOME TO PREMIUM BOT</b> 💎

╔══════════════════╗
👤 <b>Name:</b> {name}
🆔 <b>User ID:</b> <code>{user_id}</code>
╚══════════════════╝

💰 <b>Credits:</b> {user[1]}
🎁 <b>Refer System:</b> Active

📅 <b>Date:</b> {now.strftime("%Y-%m-%d")}
⏰ <b>Time:</b> {now.strftime("%I:%M %p")}

━━━━━━━━━━━━━━━━━━
😎 Invite friends & earn credits
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

    # 🔥 DAILY RESET
    if last_reset != today:
        cursor.execute("UPDATE users SET daily_used=0, last_reset=? WHERE user_id=?", (today, user_id))
        conn.commit()
        daily_used = 0

    # 🔥 FREE 5 SEARCH
    if daily_used < 5:
        cursor.execute("UPDATE users SET daily_used = daily_used + 1 WHERE user_id=?", (user_id,))
        conn.commit()
        return True

    # 🔥 CREDIT USE
    elif credits > 0:
        cursor.execute("UPDATE users SET credits = credits - 1 WHERE user_id=?", (user_id,))
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
        await update.message.reply_text("⚠️ <b>API Error</b>", parse_mode="HTML")
        return

    result_raw = data.get("result")

    if not result_raw:
        await update.message.reply_text(f"❌ <b>DATA NOT FOUND</b>\n🆔 <code>{query}</code>", parse_mode="HTML")
        return

    try:
        result = json.loads(result_raw) if isinstance(result_raw, str) else result_raw
    except:
        await update.message.reply_text("⚠️ <b>Parse Error</b>", parse_mode="HTML")
        return

    if not result.get("number"):
        await update.message.reply_text(f"❌ <b>DATA NOT FOUND</b>\n🆔 <code>{query}</code>", parse_mode="HTML")
        return

    msg = f"""
🔍 <b>RESULT FOUND</b>

╔══════════════════╗
🌍 <b>Country:</b> {result.get('country')}
📞 <b>Number:</b> <code>{result.get('number')}</code>
🆔 <b>User ID:</b> <code>{result.get('tg_id')}</code>
╚══════════════════╝

━━━━━━━━━━━━━━━━━━
👨‍💻 <b>Developer:</b> @T4HKR
"""

    await update.message.reply_text(msg, parse_mode="HTML")

# ================= /CHECK =================
async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    if not can_search(user):
        await update.message.reply_text("❌ Limit Over")
        return

    if update.message.reply_to_message:
        query = str(update.message.reply_to_message.from_user.id)
    elif context.args:
        query = context.args[0]
    else:
        await update.message.reply_text("❌ Use /check @username or reply")
        return

    await send_result(update, query)

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    text = update.message.text
    chat_type = update.effective_chat.type

    if not await check_join(user_id, context.bot):
        await update.message.reply_text("❌ Join channel first")
        return

    add_user(user_id)
    user = get_user(user_id)

    # HELP
    if text == "❓ Help":
        await update.message.reply_text(
            "📖 <b>How to use:</b>\n\n"
            "Private → send @username or ID\n"
            "Group → reply + /check\n\n"
            "💰 5 free daily + credits",
            parse_mode="HTML"
        )
        return

    # ADMIN
    if str(user_id) == str(ADMIN_ID):

        if text == "👥 Total Users":
            cursor.execute("SELECT COUNT(*) FROM users")
            await update.message.reply_text(f"👥 Total Users: {cursor.fetchone()[0]}")
            return

        if text == "💰 Add Credits":
            context.user_data["add"] = True
            await update.message.reply_text("Send: userID amount")
            return

        if context.user_data.get("add"):
            try:
                uid, amt = text.split()
                cursor.execute("UPDATE users SET credits=credits+? WHERE user_id=?", (int(amt), int(uid)))
                conn.commit()
                await update.message.reply_text("✅ Added")
            except:
                await update.message.reply_text("❌ Error")
            context.user_data["add"] = False
            return

        if text == "📢 Broadcast":
            context.user_data["bc"] = True
            await update.message.reply_text("Send message")
            return

        if context.user_data.get("bc"):
            for u in get_all_users():
                try:
                    await context.bot.send_message(u[0], text)
                except:
                    pass
            await update.message.reply_text("✅ Broadcast Done")
            context.user_data["bc"] = False
            return

    # GROUP restriction
    if chat_type != "private":
        return

    # USER BUTTONS
    if text == "💰 My Credits":
        await update.message.reply_text(f"💰 Credits: {user[1]}\n📊 Daily Left: {5-user[2]}")
        return

    if text == "🎁 Refer & Earn":
        await update.message.reply_text(f"https://t.me/{BOT_USERNAME}?start={user_id}")
        return

    if text == "🚀 Lookup Now":
        await update.message.reply_text("Send @username or userID")
        return

    # SEARCH
    if text.startswith("@") or text.isdigit():
        if not can_search(user):
            await update.message.reply_text("❌ Limit Over")
            return
        await send_result(update, text)
        return

    if update.message.reply_to_message:
        if not can_search(user):
            await update.message.reply_text("❌ Limit Over")
            return
        await send_result(update, str(update.message.reply_to_message.from_user.id))
        return

    await update.message.reply_text("❌ Invalid Input")

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("check", check_user))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
