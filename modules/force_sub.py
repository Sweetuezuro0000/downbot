from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import UserNotParticipant
from database import get_settings

async def check_force_sub(client: Client, user_id: int) -> bool:
    settings = await get_settings()
    channel = settings.get("force_sub_channel")
    if not channel:
        return True
    try:
        chat = int(channel) if str(channel).lstrip("-").isdigit() else channel
        await client.get_chat_member(chat, user_id)
        return True
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"Force Sub Exception: {e}")
        return True

async def send_force_sub_msg(client: Client, message: Message):
    settings = await get_settings()
    bot_obj = await client.get_me()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=settings.get("channel_link"))],
        [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot_obj.username}?start=start")]
    ])
    await message.reply_text(
        "⚠️ **Access Restricted!**\n\n"
        "Bot ko use karne ke liye pehle hamara main channel join karein.",
        reply_markup=keyboard
    )
