import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import (
    get_settings, update_settings, get_db_stats,
    add_premium_user, remove_premium_user, ban_user_db, unban_user_db, users_col
)

ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

def register_admin_handlers(app: Client):

    # 1. Admin Control Panel
    @app.on_message(filters.command("admin") & filters.private)
    async def admin_panel(client: Client, message: Message):
        if message.from_user.id not in ADMIN_IDS:
            return

        settings = await get_settings()
        limit_status = "🟢 ON" if settings.get("limit_system_active") else "🔴 OFF"
        maint_status = "🟢 ON" if settings.get("maintenance_mode") else "🔴 OFF"
        prem_status = "🟢 ON" if settings.get("premium_mode_active", True) else "🔴 OFF"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"Limit System: {limit_status}", callback_data="toggle_limit"),
                InlineKeyboardButton(f"Maintenance: {maint_status}", callback_data="toggle_maint")
            ],
            [
                InlineKeyboardButton(f"Premium Mode: {prem_status}", callback_data="toggle_premium"),
                InlineKeyboardButton("📊 Stats", callback_data="admin_stats")
            ]
        ])

        await message.reply_text(
            "⚙️ **Admin Control Panel**\n\nManage system toggles and settings using the buttons below:",
            reply_markup=keyboard
        )

    # 2. Callback Queries for Admin Buttons
    @app.on_callback_query(filters.regex(r"^(toggle_limit|toggle_maint|toggle_premium|admin_stats)$"))
    async def admin_callbacks(client: Client, query: CallbackQuery):
        if query.from_user.id not in ADMIN_IDS:
            await query.answer("❌ Access Denied", show_alert=True)
            return

        data = query.data
        settings = await get_settings()

        if data == "toggle_limit":
            new_val = not settings.get("limit_system_active")
            await update_settings({"limit_system_active": new_val})
            await query.answer(f"Limit System is now {'ON' if new_val else 'OFF'}")

        elif data == "toggle_maint":
            new_val = not settings.get("maintenance_mode")
            await update_settings({"maintenance_mode": new_val})
            await query.answer(f"Maintenance Mode is now {'ON' if new_val else 'OFF'}")

        elif data == "toggle_premium":
            new_val = not settings.get("premium_mode_active", True)
            await update_settings({"premium_mode_active": new_val})
            await query.answer(f"Premium Mode is now {'ON' if new_val else 'OFF'}")

        elif data == "admin_stats":
            stats = await get_db_stats()
            text = (
                "📊 **BOT DATABASE STATISTICS**\n\n"
                f"👤 **Total Users:** `{stats['total']}`\n"
                f"👑 **Premium Users:** `{stats['premium']}`\n"
                f"🚫 **Banned Users:** `{stats['banned']}`"
            )
            await query.answer()
            await query.message.reply_text(text)
            return

        # Refresh Buttons State
        new_settings = await get_settings()
        limit_status = "🟢 ON" if new_settings.get("limit_system_active") else "🔴 OFF"
        maint_status = "🟢 ON" if new_settings.get("maintenance_mode") else "🔴 OFF"
        prem_status = "🟢 ON" if new_settings.get("premium_mode_active", True) else "🔴 OFF"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"Limit System: {limit_status}", callback_data="toggle_limit"),
                InlineKeyboardButton(f"Maintenance: {maint_status}", callback_data="toggle_maint")
            ],
            [
                InlineKeyboardButton(f"Premium Mode: {prem_status}", callback_data="toggle_premium"),
                InlineKeyboardButton("📊 Stats", callback_data="admin_stats")
            ]
        ])
        await query.message.edit_reply_markup(reply_markup=keyboard)

    # 3. Broadcast Command
    @app.on_message(filters.command("broadcast") & filters.private)
    async def broadcast_cmd(client: Client, message: Message):
        if message.from_user.id not in ADMIN_IDS:
            return

        if not message.reply_to_message and len(message.command) < 2:
            await message.reply_text(
                "⚠️ **Usage:**\n"
                "1. `/broadcast Your Message Text` (Text Message)\n"
                "2. Reply to any Photo/Video/File with `/broadcast`."
            )
            return

        status_msg = await message.reply_text("📢 **Starting broadcast...**")
        
        all_users = users_col.find({})
        success = 0
        failed = 0

        async for user in all_users:
            user_id = user.get("user_id")
            try:
                if message.reply_to_message:
                    await message.reply_to_message.copy(chat_id=user_id)
                else:
                    text = message.text.split(None, 1)[1]
                    await client.send_message(chat_id=user_id, text=text)
                success += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1

        await status_msg.edit_text(
            f"✅ **Broadcast Completed!**\n\n"
            f"🎉 **Successfully Sent:** `{success}`\n"
            f"❌ **Failed / Blocked:** `{failed}`"
        )

    # 4. Add Premium Command
    @app.on_message(filters.command("add_premium") & filters.private)
    async def add_premium_cmd(client: Client, message: Message):
        if message.from_user.id not in ADMIN_IDS:
            return

        args = message.text.split()
        if len(args) < 3:
            await message.reply_text("⚠️ **Usage:** `/add_premium <user_id> <days>`\nExample: `/add_premium 123456789 30`")
            return

        try:
            target_user = int(args[1])
            days = int(args[2])
            await add_premium_user(target_user, days)
            await message.reply_text(f"✅ User `{target_user}` granted **{days} days** of Premium access.")
            
            try:
                await client.send_message(
                    target_user,
                    f"🎉 **Congratulations!** You have been granted **Premium Access** for **{days} days**! Enjoy unlimited downloads."
                )
            except Exception:
                pass

        except ValueError:
            await message.reply_text("❌ Invalid Input! User ID and Days must be numbers.")

    # 5. Remove Premium Command
    @app.on_message(filters.command("remove_premium") & filters.private)
    async def remove_premium_cmd(client: Client, message: Message):
        if message.from_user.id not in ADMIN_IDS:
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("⚠️ **Usage:** `/remove_premium <user_id>`")
            return

        try:
            target_user = int(args[1])
            await remove_premium_user(target_user)
            await message.reply_text(f"✅ Premium access revoked for user `{target_user}`.")
        except ValueError:
            await message.reply_text("❌ Invalid User ID.")

    # 6. Ban User Command
    @app.on_message(filters.command("ban") & filters.private)
    async def ban_user_cmd(client: Client, message: Message):
        if message.from_user.id not in ADMIN_IDS:
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("⚠️ **Usage:** `/ban <user_id>`")
            return

        try:
            target_user = int(args[1])
            await ban_user_db(target_user)
            await message.reply_text(f"🚫 User `{target_user}` has been banned.")
        except ValueError:
            await message.reply_text("❌ Invalid User ID.")

    # 7. Unban User Command
    @app.on_message(filters.command("unban") & filters.private)
    async def unban_user_cmd(client: Client, message: Message):
        if message.from_user.id not in ADMIN_IDS:
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("⚠️ **Usage:** `/unban <user_id>`")
            return

        try:
            target_user = int(args[1])
            await unban_user_db(target_user)
            await message.reply_text(f"✅ User `{target_user}` unbanned successfully.")
        except ValueError:
            await message.reply_text("❌ Invalid User ID.")
