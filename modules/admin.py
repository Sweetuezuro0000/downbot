import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMIN_IDS
from database import get_settings, update_setting, get_stats, users_col

def register_admin_handlers(app: Client):

    # 1. Admin Control Dashboard Panel
    @app.on_message(filters.command("admin") & filters.private & filters.user(ADMIN_IDS))
    async def admin_panel(client: Client, message: Message):
        await send_admin_dashboard(message)

    async def send_admin_dashboard(message_or_query):
        settings = await get_settings()
        total_users, banned, premium = await get_stats()

        limit_btn = "🔴 Limit System: OFF" if not settings.get("limit_system_active") else "🟢 Limit System: ON"
        maint_btn = "🔴 Maintenance: OFF" if not settings.get("maintenance_mode") else "🟢 Maintenance: ON"
        prem_btn = "🔴 Premium Mode: OFF" if not settings.get("premium_mode_active") else "🟢 Premium Mode: ON"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Stats", callback_data="admin_stats"), InlineKeyboardButton("📢 Broadcast", callback_data="admin_bcast")],
            [InlineKeyboardButton(limit_btn, callback_data="toggle_limit"), InlineKeyboardButton(maint_btn, callback_data="toggle_maint")],
            [InlineKeyboardButton(prem_btn, callback_data="toggle_prem")],
            [InlineKeyboardButton("❌ Close Panel", callback_data="admin_close")]
        ])

        text = (
            "🎛️ **ADMIN CONTROL PANEL**\n\n"
            f"👥 **Total Users:** `{total_users}` | 🚫 **Banned:** `{banned}`\n"
            f"⭐ **Premium Users:** `{premium}`\n"
            f"⏱️ **Daily Limit:** `{settings.get('daily_free_limit')}` per user\n\n"
            "⚡ *Niche diye gaye buttons se instant settings ON/OFF karein:*"
        )

        if isinstance(message_or_query, CallbackQuery):
            await message_or_query.message.edit_text(text, reply_markup=keyboard)
        else:
            await message_or_query.reply_text(text, reply_markup=keyboard)

    # 2. Callback Handling for Toggles
    @app.on_callback_query(filters.regex(r"^(toggle_|admin_)") & filters.user(ADMIN_IDS))
    async def admin_callbacks(client: Client, query: CallbackQuery):
        data = query.data
        settings = await get_settings()

        if data == "toggle_limit":
            new_val = not settings.get("limit_system_active")
            await update_setting("limit_system_active", new_val)
            await query.answer(f"Limit System: {'ON' if new_val else 'OFF'}")
            await send_admin_dashboard(query)

        elif data == "toggle_maint":
            new_val = not settings.get("maintenance_mode")
            await update_setting("maintenance_mode", new_val)
            await query.answer(f"Maintenance Mode: {'ON' if new_val else 'OFF'}")
            await send_admin_dashboard(query)

        elif data == "toggle_prem":
            new_val = not settings.get("premium_mode_active")
            await update_setting("premium_mode_active", new_val)
            await query.answer(f"Premium Mode: {'ON' if new_val else 'OFF'}")
            await send_admin_dashboard(query)

        elif data == "admin_stats":
            total_users, banned, premium = await get_stats()
            await query.answer(f"Users: {total_users} | Banned: {banned} | Premium: {premium}", show_alert=True)

        elif data == "admin_bcast":
            await query.answer("Broadcast karne ke liye command use karein: /broadcast <your message>", show_alert=True)

        elif data == "admin_close":
            await query.message.delete()

    # 3. Broadcast System
    @app.on_message(filters.command("broadcast") & filters.private & filters.user(ADMIN_IDS))
    async def broadcast(client: Client, message: Message):
        if not message.reply_to_message and len(message.command) < 2:
            await message.reply_text("❌ Message ke sath reply karein ya text likhein: `/broadcast Hello Users`")
            return

        status = await message.reply_text("🚀 Broadcast start ho raha hai...")
        users = users_col.find({})
        success, failed = 0, 0

        async for user in users:
            try:
                if message.reply_to_message:
                    await message.reply_to_message.copy(user["user_id"])
                else:
                    msg_text = message.text.split(maxsplit=1)[1]
                    await client.send_message(user["user_id"], msg_text)
                success += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1

        await status.edit_text(f"✅ **Broadcast Done!**\n\n🟢 Success: `{success}`\n🔴 Failed: `{failed}`")
