from pyrogram import Client, filters
from pyrogram.types import Message
from database import get_user, get_settings

def register_referral_handlers(app: Client):

    @app.on_message(filters.command("refer") & filters.private)
    async def refer_command(client: Client, message: Message):
        user_id = message.from_user.id
        bot = await client.get_me()
        user_data = await get_user(user_id)
        settings = await get_settings()
        
        ref_link = f"https://t.me/{bot.username}?start=ref_{user_id}"
        total_refs = user_data.get("total_referrals", 0) if user_data else 0
        base_limit = settings.get("daily_free_limit", 5)
        bonus_downloads = total_refs * 2
        total_limit = base_limit + bonus_downloads

        text = (
            "🎯 **REFER & EARN PROGRAM**\n\n"
            f"🔗 **Aapka Referral Link:**\n`{ref_link}`\n\n"
            f"📊 **Total Referrals:** `{total_refs}` Users\n"
            f"🎁 **Bonus Earned:** `+{bonus_downloads}` Extra Daily Downloads\n"
            f"⚡ **Aapka Total Daily Limit:** `{total_limit}` Downloads/Day\n\n"
            "💡 *Har 1 Dost ko invite karne par +2 Extra Downloads Daily milenge!*"
        )
        await message.reply_text(text)
