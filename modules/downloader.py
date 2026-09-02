import os
import asyncio
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message
from database import get_settings, get_user, check_and_reset_limit, increment_download_count
from modules.force_sub import check_force_sub, send_force_sub_msg

URL_REGEX = r"(https?://[^\s]+)"

def download_media_sync(url: str, output_path: str):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 100 * 1024 * 1024, # 100MB
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', 'Social Media Video')

def register_downloader_handlers(app: Client):

    @app.on_message(filters.regex(URL_REGEX) & filters.private)
    async def handle_download(client: Client, message: Message):
        user_id = message.from_user.id
        settings = await get_settings()

        # 1. Check Maintenance Mode
        if settings.get("maintenance_mode"):
            await message.reply_text("🛠️ **Bot Under Maintenance!** Kuch der baad try karein.")
            return

        # 2. Check Force-Sub
        if not await check_force_sub(client, user_id):
            await send_force_sub_msg(client, message)
            return

        # 3. Check Daily Limit System (IF ENABLED BY ADMIN)
        if settings.get("limit_system_active"):
            user_data = await get_user(user_id)
            if not user_data.get("is_premium"):
                downloads_today = await check_and_reset_limit(user_id)
                daily_limit = settings.get("daily_free_limit", 5)
                
                if downloads_today >= daily_limit:
                    await message.reply_text(
                        f"❌ **Daily Free Limit Over! ({downloads_today}/{daily_limit})**\n\n"
                        "Apne dosto ko refer karein `/refer` ya Premium access lein!"
                    )
                    return

        url = message.text.strip()
        status_msg = await message.reply_text("⏳ **Media extract ho raha hai... Please wait.**")

        os.makedirs("downloads", exist_ok=True)
        base_filename = f"downloads/{user_id}_{message.id}"
        file_id = f"{base_filename}.mp4"

        try:
            # Sync execution in thread
            title = await asyncio.to_thread(download_media_sync, url, file_id)

            actual_file = file_id
            if not os.path.exists(file_id):
                for f in os.listdir("downloads"):
                    if f.startswith(f"{user_id}_{message.id}"):
                        actual_file = os.path.join("downloads", f)
                        break

            if not os.path.exists(actual_file):
                await status_msg.edit_text("❌ **Download Failed!** Video process nahi ho saki.")
                return

            await status_msg.edit_text("📤 **Video Upload Ho Rahi Hai...**")

            # Ad Caption Format
            ad_text = settings.get("ad_caption", "").format(channel_link=settings.get("channel_link", ""))
            caption = f"🎬 **{title[:60]}**{ad_text}"

            await message.reply_video(
                video=actual_file,
                caption=caption,
                supports_streaming=True
            )
            
            # Count increment only if limit system is active
            if settings.get("limit_system_active"):
                await increment_download_count(user_id)

            await status_msg.delete()

        except Exception as e:
            print(f"Download Error: {e}")
            await status_msg.edit_text("❌ **Error:** Video download nahi ho saki. Link check karein.")

        finally:
            # Cleanup File
            for f in os.listdir("downloads"):
                if f.startswith(f"{user_id}_{message.id}"):
                    try:
                        os.remove(os.path.join("downloads", f))
                    except Exception:
                        pass
