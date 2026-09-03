import os
import time
import asyncio
import uuid
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import get_settings, get_user, check_and_reset_limit, increment_download_count
from modules.force_sub import check_force_sub, send_force_sub_msg

URL_REGEX = r"(https?://[^\s]+)"

# Temporary Cache for Links (Callback Data 64-byte limit workaround)
URL_CACHE = {}

def download_media_sync(url: str, output_path: str, is_audio: bool = False):
    if is_audio:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path + '.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 1900 * 1024 * 1024,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        ydl_opts = {
            'format': 'bv*[height<=1080]+ba/b[height<=1080]/b',
            'outtmpl': output_path + '.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 1900 * 1024 * 1024,
            'merge_output_format': 'mp4',
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', 'Social Media Media')

# --- Live Progress Bar Callback ---
async def progress_bar(current, total, status_msg, start_time, action_text="Upload"):
    now = time.time()
    # Rate limit status updates to every 3.5 seconds to prevent Telegram FloodWait
    if hasattr(status_msg, "last_update_time") and now - status_msg.last_update_time < 3.5:
        return
    status_msg.last_update_time = now

    percentage = current * 100 / total
    completed = int(percentage // 10)
    progress = "█" * completed + "░" * (10 - completed)
    
    speed = current / (now - start_time) if (now - start_time) > 0 else 0
    speed_mb = speed / (1024 * 1024)
    
    curr_mb = current / (1024 * 1024)
    total_mb = total / (1024 * 1024)

    text = (
        f"📤 **{action_text} Progress:**\n\n"
        f"[{progress}] `{percentage:.1f}%`\n\n"
        f"🚀 **Speed:** `{speed_mb:.2f} MB/s`\n"
        f"📦 **Size:** `{curr_mb:.1f} MB` / `{total_mb:.1f} MB`"
    )
    try:
        await status_msg.edit_text(text)
    except Exception:
        pass

def register_downloader_handlers(app: Client):

    # 1. Capture Link & Ask for Format Selection
    @app.on_message(filters.regex(URL_REGEX) & filters.private)
    async def handle_url(client: Client, message: Message):
        user_id = message.from_user.id
        settings = await get_settings()

        if settings.get("maintenance_mode"):
            await message.reply_text("🛠️ **Bot Under Maintenance!** Kuch der baad try karein.")
            return

        if not await check_force_sub(client, user_id):
            await send_force_sub_msg(client, message)
            return

        url = message.text.strip()
        link_id = str(uuid.uuid4())[:8]
        URL_CACHE[link_id] = url

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 Download Video", callback_data=f"dl_vid_{link_id}"),
                InlineKeyboardButton("🎵 Extract MP3", callback_data=f"dl_aud_{link_id}")
            ]
        ])

        await message.reply_text(
            "🎯 **Select Format:**\nChoose karein aapko Video chahiye ya Audio (MP3):",
            reply_markup=keyboard,
            quote=True
        )

    # 2. Process Format Selection
    @app.on_callback_query(filters.regex(r"^dl_(vid|aud)_"))
    async def process_download(client: Client, query: CallbackQuery):
        user_id = query.from_user.id
        settings = await get_settings()

        # Limit Check
        if settings.get("limit_system_active"):
            user_data = await get_user(user_id)
            is_premium = user_data.get("is_premium", False) if user_data else False
            
            if not is_premium:
                downloads_today = await check_and_reset_limit(user_id)
                base_limit = settings.get("daily_free_limit", 5)
                referrals = user_data.get("total_referrals", 0) if user_data else 0
                total_allowed = base_limit + (referrals * 2)

                if downloads_today >= total_allowed:
                    await query.answer("❌ Daily Download Limit Over!", show_alert=True)
                    await query.message.edit_text(
                        f"❌ **Daily Download Limit Reached!**\n\n"
                        f"📊 Aaj ke downloads: `{downloads_today}/{total_allowed}`\n"
                        f"💡 **Tip:** Friends ko refer karke `/refer` per referral **+2 Extra Downloads** paayein!"
                    )
                    return

        data_parts = query.data.split("_")
        dl_type = data_parts[1]
        link_id = data_parts[2]

        url = URL_CACHE.get(link_id)
        if not url:
            await query.answer("⚠️ Link expire ho gaya hai, please link dobara bhejien!", show_alert=True)
            return

        is_audio = (dl_type == "aud")
        await query.answer("⚡ Process start ho gaya hai...")
        status_msg = await query.message.edit_text("⏳ **Media extract ho raha hai... Please wait.**")

        os.makedirs("downloads", exist_ok=True)
        base_filename = f"downloads/{user_id}_{query.message.id}"

        try:
            title = await asyncio.to_thread(download_media_sync, url, base_filename, is_audio)

            actual_file = None
            for f in os.listdir("downloads"):
                if f.startswith(f"{user_id}_{query.message.id}"):
                    actual_file = os.path.join("downloads", f)
                    break

            if not actual_file or not os.path.exists(actual_file):
                await status_msg.edit_text("❌ **Download Failed!** File process nahi ho saki.")
                return

            ad_text = settings.get("ad_caption", "").format(channel_link=settings.get("channel_link", ""))
            caption = f"🎬 **{title[:60]}**{ad_text}"

            start_time = time.time()
            status_msg.last_update_time = 0

            # Send File with Progress Bar
            if is_audio:
                await client.send_audio(
                    chat_id=query.message.chat.id,
                    audio=actual_file,
                    caption=caption,
                    progress=progress_bar,
                    progress_args=(status_msg, start_time, "Audio Upload")
                )
            else:
                await client.send_video(
                    chat_id=query.message.chat.id,
                    video=actual_file,
                    caption=caption,
                    supports_streaming=True,
                    progress=progress_bar,
                    progress_args=(status_msg, start_time, "Video Upload")
                )

            if settings.get("limit_system_active"):
                await increment_download_count(user_id)

            await status_msg.delete()

        except Exception as e:
            print(f"Download Error: {e}")
            await status_msg.edit_text("❌ **Error:** Media download/upload nahi ho saka.")

        finally:
            # Cleanup
            URL_CACHE.pop(link_id, None)
            for f in os.listdir("downloads"):
                if f.startswith(f"{user_id}_{query.message.id}"):
                    try:
                        os.remove(os.path.join("downloads", f))
                    except Exception:
                        pass
