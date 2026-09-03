from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import UserNotParticipant
from config import FORCE_SUB_CHANNEL, CHANNEL_LINK

async def check_force_sub(client: Client, user_id: int) -> bool:
    if not FORCE_SUB_CHANNEL:
        return True
    try:
        chat = int(FORCE_SUB_CHANNEL) if str(FORCE_SUB_CHANNEL).lstrip("-").isdigit() else FORCE_SUB_CHANNEL
        await client.get_chat_member(chat, user_id)
        return True
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"Force Sub Error: {e}")
        return True  # Verification fail hone par download block na hone de

async def send_force_sub_msg(client: Client, message: Message):
    bot_obj = await client.get_me()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot_obj.username}?start=start")]
    ])
    await message.reply_text(
        "⚠️ **Access Restricted!**\n\n"
        "Bot use karne ke liye pehle hamara main channel join karein.",
        reply_markup=keyboard
    )
