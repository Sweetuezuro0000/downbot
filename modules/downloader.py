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
        # Universal format selector: YouTube, Pinterest, Insta, TikTok, Twitter sab par chalega
        'format': 'bv*[height<=1080]+ba/b[height<=1080]/b',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 1900 * 1024 * 1024, # 1.9 GB Limit
        'merge_output_format': 'mp4', # FFmpeg automatic MP4 container me convert kar dega
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', 'Social Media Video')

def register_downloader_handlers(app: Client):

    @app.on_message(filters.regex(URL_REGEX) & filters.private)
    async def handle_download(client: Client, message: Message):
        user_id = message.from_user.id
        settings = await get_settings()

        # 1. Maintenance Check
        if settings.get("maintenance_mode"):
            await message.reply_text("🛠️ **Bot Under Maintenance!** Kuch der baad try karein.")
            return

        # 2. Force-Sub Check
        if not await check_force_sub(client, user_id):
            await send_force_sub_msg(client, message)
            return

        # 3. Limit Check
        if settings.get("limit_system_active"):
            user_data = await get_user(user_id)
            is_premium = user_data.get("is_premium", False) if user_data else False
            
            if not is_premium:
                downloads_today = await check_and_reset_limit(user_id)
                base_limit = settings.get("daily_free_limit", 5)
                referrals = user_data.get("total_referrals", 0) if user_data else 0
                
                total_allowed = base_limit + (referrals * 2)

                if downloads_today >= total_allowed:
                    await message.reply_text(
                        f"❌ **Daily Download Limit Reached!**\n\n"
                        f"📊 Aaj ke downloads: `{downloads_today}/{total_allowed}`\n"
                        f"💡 **Tip:** Friends ko refer karke `/refer` per referral **+2 Extra Downloads** paayein!"
                    )
                    return

        url = message.text.strip()
        status_msg = await message.reply_text("⏳ **Media extract ho raha hai... Please wait.**")

        os.makedirs("downloads", exist_ok=True)
        base_filename = f"downloads/{user_id}_{message.id}"
        file_id = f"{base_filename}.mp4"

        try:
            # Universal sync download execution
            title = await asyncio.to_thread(download_media_sync, url, file_id)

            actual_file = file_id
            if not os.path.exists(file_id):
                for f in os.listdir("downloads"):
                    if f.startswith(f"{user_id}_{message.id}"):
                        actual_file = os.path.join("downloads", f)
                        break

            if not os.path.exists(actual_file):
                await status_msg.edit_text("❌ **Download Failed!** Video format process nahi ho saka.")
                return

            await status_msg.edit_text("📤 **Video Upload Ho Rahi Hai...**")

            ad_text = settings.get("ad_caption", "").format(channel_link=settings.get("channel_link", ""))
            caption = f"🎬 **{title[:60]}**{ad_text}"

            await message.reply_video(
                video=actual_file,
                caption=caption,
                supports_streaming=True
            )
            
            if settings.get("limit_system_active"):
                await increment_download_count(user_id)
                
            await status_msg.delete()

        except Exception as e:
            print(f"Download Error: {e}")
            await status_msg.edit_text("❌ **Error:** Video download nahi ho saki. Link check karein.")

        finally:
            # File Cleanup
            for f in os.listdir("downloads"):
                if f.startswith(f"{user_id}_{message.id}"):
                    try:
                        os.remove(os.path.join("downloads", f))
                    except Exception:
                        pass
