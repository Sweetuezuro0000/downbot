import os
import time
import glob
import shutil
import asyncio
import uuid
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import get_settings, get_user, check_and_reset_limit, increment_download_count
from modules.force_sub import check_force_sub, send_force_sub_msg

URL_REGEX = r"(https?://[^\s]+)"

# Temporary cache for handling callback queries
URL_CACHE = {}

def download_media_sync(url: str, output_dir: str, is_audio: bool = False):
    if is_audio:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"{output_dir}/%(title).30s_%(id)s.%(ext)s",
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
            'outtmpl': f"{output_dir}/%(title).30s_%(id)s.%(ext)s",
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 1900 * 1024 * 1024,
            'merge_output_format': 'mp4',
            'allow_playlist_files': True,  # Required for Instagram Carousels
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', 'Social Media Media')

# Live Upload Progress Bar Callback
async def progress_bar(current, total, status_msg, start_time, action_text="Uploading"):
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

    # 1. Capture Link & Present Format Selection Keyboard
    @app.on_message(filters.regex(URL_REGEX) & filters.private)
    async def handle_url(client: Client, message: Message):
        user_id = message.from_user.id
        settings = await get_settings()

        # Maintenance Check
        if settings.get("maintenance_mode"):
            admin_ids = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
            if user_id not in admin_ids:
                await message.reply_text("🛠️ **Bot is under maintenance!** Please try again later.")
                return

        # Force-Sub Check
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
            "🎯 **Select Download Format:**\nChoose whether you want Video or Audio (MP3):",
            reply_markup=keyboard,
            quote=True
        )

    # 2. Process Download Selection Callback
    @app.on_callback_query(filters.regex(r"^dl_(vid|aud)_"))
    async def process_download(client: Client, query: CallbackQuery):
        user_id = query.from_user.id
        settings = await get_settings()

        # Check Limits
        limit_active = settings.get("limit_system_active", True)
        user_data = await get_user(user_id)
        is_premium = user_data.get("is_premium", False) if user_data else False

        if limit_active and not is_premium:
            downloads_today = await check_and_reset_limit(user_id)
            base_limit = settings.get("daily_free_limit", 5)
            referrals = user_data.get("total_referrals", 0) if user_data else 0
            total_allowed = base_limit + (referrals * 2)

            if downloads_today >= total_allowed:
                await query.answer("❌ Daily Download Limit Reached!", show_alert=True)
                await query.message.edit_text(
                    f"❌ **Daily Download Limit Reached!**\n\n"
                    f"📊 Downloads Today: `{downloads_today}/{total_allowed}`\n"
                    f"💡 **Tip:** Invite friends using `/refer` to get **+2 Extra Downloads** per referral!"
                )
                return

        data_parts = query.data.split("_")
        dl_type = data_parts[1]
        link_id = data_parts[2]

        url = URL_CACHE.get(link_id)
        if not url:
            await query.answer("⚠️ Link session expired. Please resend the link!", show_alert=True)
            return

        is_audio = (dl_type == "aud")
        await query.answer("⚡ Processing download...")
        status_msg = await query.message.edit_text("⏳ **Fetching media details... Please wait.**")

        download_dir = f"downloads/{user_id}_{query.message.id}"
        os.makedirs(download_dir, exist_ok=True)

        try:
            # Download media in a separate thread
            title = await asyncio.to_thread(download_media_sync, url, download_dir, is_audio)

            downloaded_files = glob.glob(f"{download_dir}/*")
            if not downloaded_files:
                await status_msg.edit_text("❌ **Download Failed!** Media could not be processed.")
                return

            await status_msg.edit_text("📤 **Preparing media upload...**")

            channel_link = settings.get("channel_link", "https://t.me/YourChannel")
            custom_caption = f"🎬 **{title[:60]}**\n\n🚀 **Join:** {channel_link}"

            start_time = time.time()
            status_msg.last_update_time = 0

            # Filter audio files vs video/image files
            media_files = [f for f in downloaded_files if not f.endswith(('.jpg', '.webp', '.png'))]
            if not media_files:
                media_files = downloaded_files

            # Upload all items (Supports Single Video/Audio and Instagram Carousels)
            for file_path in media_files:
                if is_audio or file_path.endswith('.mp3'):
                    await client.send_audio(
                        chat_id=query.message.chat.id,
                        audio=file_path,
                        caption=custom_caption,
                        progress=progress_bar,
                        progress_args=(status_msg, start_time, "Audio Upload")
                    )
                elif file_path.endswith(('.mp4', '.mkv', '.webm', '.mov')):
                    await client.send_video(
                        chat_id=query.message.chat.id,
                        video=file_path,
                        caption=custom_caption,
                        supports_streaming=True,
                        progress=progress_bar,
                        progress_args=(status_msg, start_time, "Video Upload")
                    )
                else:
                    await client.send_document(
                        chat_id=query.message.chat.id,
                        document=file_path,
                        caption=custom_caption
                    )

            if limit_active and not is_premium:
                await increment_download_count(user_id)

            await status_msg.delete()

        except Exception as e:
            print(f"Download Error: {e}")
            await status_msg.edit_text(f"❌ **Error:** Download/Upload failed. `{str(e)[:100]}`")

        finally:
            # Cleanup Cache and Disk
            URL_CACHE.pop(link_id, None)
            if os.path.exists(download_dir):
                shutil.rmtree(download_dir, ignore_errors=True)
