import os
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
from database import get_settings

# Config/Env fallback
ENV_CHANNEL = os.getenv("FORCE_SUB_CHANNEL")
ENV_LINK = os.getenv("CHANNEL_LINK")

async def check_force_sub(client: Client, user_id: int) -> bool:
    settings = await get_settings() or {}
    
    # Database se lo, agar wahan empty mile toh .env se fetch karo
    channel = settings.get("force_sub_channel") or ENV_CHANNEL
    if not channel:
        return True # FSub disabled

    try:
        chat = int(channel) if str(channel).lstrip("-").isdigit() else str(channel)
        member = await client.get_chat_member(chat, user_id)
        
        # Status check (Pyrogram 'left' status return kar sakta hai)
        status = str(member.status).lower()
        if "left" in status or "banned" in status or "kicked" in status:
            return False
            
        return True

    except UserNotParticipant:
        return False
    except ChatAdminRequired:
        print("⚠️ Bot Force Sub channel me ADMIN nahi hai!")
        return True # Bot crash na ho isliye allow kar do
    except Exception as e:
        print(f"Force Sub Exception: {e}")
        return True

async def send_force_sub_msg(client: Client, message: Message):
    settings = await get_settings() or {}
    
    # Database ya Env se link fetch karein
    raw_link = settings.get("channel_link") or ENV_LINK or "https://t.me"
    
    # URL ko properly format karein (URL_INVALID error se bachne ke liye)
    if raw_link.startswith("@"):
        link = f"https://t.me/{raw_link[1:]}"
    elif not raw_link.startswith("http://") and not raw_link.startswith("https://"):
        link = f"https://t.me/{raw_link}"
    else:
        link = raw_link

    bot_obj = await client.get_me()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=link)],
        [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot_obj.username}?start=start")]
    ])
    
    await message.reply_text(
        "⚠️ **Access Restricted!**\n\n"
        "Join our channel to use this bot.",
        reply_markup=keyboard
    )
