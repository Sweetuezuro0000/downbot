import os
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant

FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "").strip()
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

async def check_force_sub(client: Client, user_id: int) -> bool:
    # 1. If force sub channel is not set, allow access
    if not FORCE_SUB_CHANNEL:
        return True

    # 2. Bypass force sub check for Admins
    if user_id in ADMIN_IDS:
        return True

    try:
        channel = FORCE_SUB_CHANNEL.replace("@", "").strip()
        chat_target = f"@{channel}" if not channel.startswith("-") else int(channel)

        member = await client.get_chat_member(chat_id=chat_target, user_id=user_id)
        if member.status in ["owner", "administrator", "member"]:
            return True
        return False

    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"Force Sub Error: {e}")
        # If bot is not admin in channel or channel ID is wrong, allow user
        return True

async def send_force_sub_msg(client: Client, message: Message):
    channel = FORCE_SUB_CHANNEL.replace("@", "").strip()
    channel_url = f"https://t.me/{channel}" if not channel.startswith("-") else "https://t.me/"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Update Channel", url=channel_url)],
        [InlineKeyboardButton("🔄 Refresh / Try Again", url=f"https://t.me/{client.me.username}?start=start")]
    ])

    await message.reply_text(
        "⚠️ **Channel Subscription Required!**\n\n"
        "You must join our update channel to use this bot. Click below to join and try again:",
        reply_markup=keyboard,
        quote=True
    )
