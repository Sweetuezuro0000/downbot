from pyrogram import Client, filters
from pyrogram.types import Message
from database import get_user, add_user, get_settings

def register_referral_handlers(app: Client):

    @app.on_message(filters.command("refer") & filters.private)
    async def refer_command(client: Client, message: Message):
        user_id = message.from_user.id
        bot = await client.get_me()
        user_data = await get_user(user_id)
        
        ref_link = f"https://t.me/{bot.username}?start=ref_{user_id}"
        total_refs = user_data.get("total_referrals", 0) if user_data else 0

        text = (
            "🎯 **REFER & EARN PROGRAM**\n\n"
            f"🔗 **Aapka Referral Link:**\n`{ref_link}`\n\n"
            f"📊 **Aapke Total Referrals:** `{total_refs}` User(s)\n\n"
            "💡 Apne dosto ko invite karein aur Extra Download Benefits paayein!"
        )
        await message.reply_text(text)
