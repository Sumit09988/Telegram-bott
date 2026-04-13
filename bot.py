async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    text = update.message.text
    chat_type = update.effective_chat.type

    if not await check_join(user_id, context.bot):
        await update.message.reply_text(
            "❌ Join all channels first",
            reply_markup=join_buttons()
        )
        return

    add_user(user_id)
    user = get_user(user_id)

    # ================= HELP =================
    if text == "❓ Help":
        await update.message.reply_text(
            "📖 Use:\n\nPrivate: @username / ID\nGroup: /check reply\n\n💰 5 daily + credits"
        )
        return

    # ================= ADMIN =================
    if str(user_id) == str(ADMIN_ID):

        if text == "👥 Total Users":
            cursor.execute("SELECT COUNT(*) FROM users")
            await update.message.reply_text(f"👥 Users: {cursor.fetchone()[0]}")
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
            await update.message.reply_text("✅ Done")
            context.user_data["bc"] = False
            return

    # ================= GROUP BLOCK =================
    if chat_type != "private":
        return

    # ================= USER BUTTONS =================
    if text == "💰 My Credits":
        await update.message.reply_text(f"Credits: {user[1]}\nDaily Left: {5-user[2]}")
        return

    if text == "🎁 Refer & Earn":
        await update.message.reply_text(f"https://t.me/{BOT_USERNAME}?start={user_id}")
        return

    # 🚀 LOOKUP BUTTON MODE
    if text == "🚀 Lookup Now":
        context.user_data["lookup"] = True
        await update.message.reply_text("Send @username or userID")
        return

    # 🔥 LOOKUP MODE ACTIVE (SAFE CHECK)
    if context.user_data.get("lookup") and (text.startswith("@") or text.isdigit()):
        context.user_data["lookup"] = False

        if not can_search(user):
            await update.message.reply_text("❌ Limit Over")
            return

        await send_result(update, text)
        return

    # ================= DIRECT SEARCH =================
    if text.startswith("@") or text.isdigit():
        if not can_search(user):
            await update.message.reply_text("❌ Limit Over")
            return
        await send_result(update, text)
        return

    # ================= REPLY SEARCH =================
    if update.message.reply_to_message:
        if not can_search(user):
            await update.message.reply_text("❌ Limit Over")
            return
        await send_result(update, str(update.message.reply_to_message.from_user.id))
        return

    await update.message.reply_text("❌ Invalid Input")
