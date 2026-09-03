import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid

FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "").strip()
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

def get_channel_target():
    if not FORCE_SUB_CHANNEL:
        return None
    ch = FORCE_SUB_CHANNEL.strip()
    if ch.startswith("-100") or (ch.startswith("-") and ch[1:].isdigit()) or ch.isdigit():
        return int(ch)
    if not ch.startswith("@"):
        return f"@{ch}"
    return ch

async def check_force_sub(client: Client, user_id: int) -> bool:
    if not FORCE_SUB_CHANNEL:
        return True

    # Bypass check for Admins
    if user_id in ADMIN_IDS:
        return True

    target = get_channel_target()
    if not target:
        return True

    try:
        member = await client.get_chat_member(chat_id=target, user_id=user_id)
        # Convert enum status to lower string for universal matching across Pyrogram versions
        status = str(member.status).lower()
        if any(s in status for s in ["owner", "administrator", "member"]):
            return True
        return False

    except UserNotParticipant:
        return False
    except (ChatAdminRequired, PeerIdInvalid) as e:
        print(f"⚠️ [FSub Warning] Bot is NOT admin in channel {FORCE_SUB_CHANNEL}: {e}")
        return True
    except Exception as e:
        print(f"⚠️ [FSub Error]: {e}")
        return False

async def send_force_sub_msg(client: Client, message: Message):
    target = get_channel_target()
    if isinstance(target, str) and target.startswith("@"):
        channel_url = f"https://t.me/{target.replace('@', '')}"
    else:
        channel_url = os.environ.get("FORCE_SUB_URL", "https://t.me/YourChannel")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Update Channel", url=channel_url)],
        [InlineKeyboardButton("🔄 Verify Subscription", callback_data="verify_fsub")]
    ])

    await message.reply_text(
        "⚠️ **Channel Subscription Required!**\n\n"
        "You must join our channel to use this bot.\n"
        "Please join using the button below and click **Verify Subscription**.",
        reply_markup=keyboard,
        quote=True
    )

def register_force_sub_handlers(app: Client):
    @app.on_callback_query(filters.regex("^verify_fsub$"))
    async def verify_fsub_callback(client: Client, query: CallbackQuery):
        user_id = query.from_user.id
        is_subscribed = await check_force_sub(client, user_id)

        if is_subscribed:
            await query.answer("✅ Thank you! Subscription verified. You can now use the bot.", show_alert=True)
            await query.message.delete()
        else:
            await query.answer("❌ You haven't joined the channel yet! Please join and try again.", show_alert=True)
