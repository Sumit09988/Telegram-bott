import requests
import json
from datetime import datetime, date
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from config import *
from database import *

# ================= UI =================
user_keyboard = [
    ["🚀 Lookup Now"],
    ["💰 My Credits", "🎁 Refer & Earn"],
    ["📊 Stats", "❓ Help"]
]

admin_keyboard = [
    ["👥 Total Users"],
    ["💰 Add Credits"],
    ["📢 Broadcast"]
]

# ================= JOIN BUTTON =================
def join_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Channel 1", url=f"https://t.me/{CHANNELS[0].replace('@','')}")],
        [InlineKeyboardButton("📢 Channel 2", url=f"https://t.me/{CHANNELS[1].replace('@','')}")]
    ])

# ================= CHANNEL CHECK =================
async def check_join(user_id, bot):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name

    if not await check_join(user_id, context.bot):
        await update.message.reply_text("❌ Join all channels first", reply_markup=join_buttons())
        return

    is_new = not user_exists(user_id)

    ref = None
    if context.args:
        try:
            ref = int(context.args[0])
        except:
            pass

    add_user(user_id, ref)

    if is_new:
        try:
            await context.bot.send_message(ADMIN_ID, f"🆕 New User: {user_id}")
        except:
            pass

    if is_new and ref and ref != user_id:
        add_credit(ref)
        try:
            await context.bot.send_message(ref, "🎉 Referral joined! +1 Credit")
        except:
            pass

    user = get_user(user_id)
    now = datetime.now()

    msg = f"""
💎 <b>WELCOME TO PREMIUM BOT</b>

👤 {name}
🆔 <code>{user_id}</code>

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

# ================= FIX START =================
async def start_fix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower().startswith("/start"):
        await start(update, context)

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
        return requests.get(url, timeout=10).json()
    except:
        return None

async def send_result(update, query):
    url = f"http://eris-osint.vercel.app/info?key={API_KEY}&id={query}"
    data = fetch_data(url)

    if not data:
        await update.message.reply_text("⚠️ API Error")
        return

    result = data.get("result")

    if not result:
        await update.message.reply_text("❌ Data not found\n🆔 UID Generated: " + str(query))
        return

    try:
        result = json.loads(result) if isinstance(result, str) else result
    except:
        await update.message.reply_text("⚠️ Parse Error")
        return

    msg = f"""
🔍 <b>RESULT FOUND</b>

🌍 Country: {result.get('country')}
📞 Number: <code>{result.get('number')}</code>
🆔 User ID: <code>{result.get('tg_id')}</code>
"""
    await update.message.reply_text(msg, parse_mode="HTML")

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if update.effective_chat.type != "private":
        return

    if not await check_join(user_id, context.bot):
        await update.message.reply_text("❌ Join channels first", reply_markup=join_buttons())
        return

    add_user(user_id)
    user = get_user(user_id)

    # ================= USER =================
    if text == "💰 My Credits":
        await update.message.reply_text(f"💰 {user[1]} credits\n📊 Left: {5-user[2]}")
        return

    if text == "📊 Stats":
        await update.message.reply_text(f"📊 Used Today: {user[2]}/5")
        return

    if text == "🎁 Refer & Earn":
        await update.message.reply_text(f"https://t.me/{BOT_USERNAME}?start={user_id}")
        return

    if text == "❓ Help":
        await update.message.reply_text("Send @username or ID")
        return

    if text == "🚀 Lookup Now":
        context.user_data["lookup"] = True
        await update.message.reply_text("Send @username or ID")
        return

    # ================= LOOKUP =================
    if text.startswith("@") or text.isdigit():
        if not can_search(user):
            await update.message.reply_text("❌ Limit Over")
            return
        await send_result(update, text)
        return

    # ================= ADMIN =================
    if str(user_id) == str(ADMIN_ID):

        if text == "👥 Total Users":
            cursor.execute("SELECT COUNT(*) FROM users")
            await update.message.reply_text(f"👥 {cursor.fetchone()[0]}")
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
                await update.message.reply_text("✅ Done")
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

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.COMMAND, start_fix))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🚀 Bot running...")

app.run_polling()
