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
        # Max 1080p resolution to avoid huge 4K file sizes
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 1900 * 1024 * 1024, # 1.9 GB Limit (Telegram Max Limit)
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

        # 3. Independent Limit System Check
        if settings.get("limit_system_active"):
            user_data = await get_user(user_id)
            is_premium = user_data.get("is_premium", False) if user_data else False
            
            # Limit check ONLY applies to non-premium users when Limit System is ON
            if not is_premium:
                downloads_today = await check_and_reset_limit(user_id)
                base_limit = settings.get("daily_free_limit", 5)
                referrals = user_data.get("total_referrals", 0) if user_data else 0
                
                # Bonus: Every referral gives +2 daily downloads
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
            # Sync execution in thread pool
            title = await asyncio.to_thread(download_media_sync, url, file_id)

            actual_file = file_id
            if not os.path.exists(file_id):
                for f in os.listdir("downloads"):
                    if f.startswith(f"{user_id}_{message.id}"):
                        actual_file = os.path.join("downloads", f)
                        break

            if not os.path.exists(actual_file):
                await status_msg.edit_text("❌ **Download Failed!** Video process nahi ho saki ya size 1.9GB se bada hai.")
                return

            await status_msg.edit_text("📤 **Video Upload Ho Rahi Hai...**")

            ad_text = settings.get("ad_caption", "").format(channel_link=settings.get("channel_link", ""))
            caption = f"🎬 **{title[:60]}**{ad_text}"

            await message.reply_video(
                video=actual_file,
                caption=caption,
                supports_streaming=True
            )
            
            # Increment download count
            await increment_download_count(user_id)
            await status_msg.delete()

        except Exception as e:
            print(f"Download Error: {e}")
            await status_msg.edit_text("❌ **Error:** Download fail ho gaya. Link sahi hai ya nahi check karein.")

        finally:
            # Auto Cleanup
            for f in os.listdir("downloads"):
                if f.startswith(f"{user_id}_{message.id}"):
                    try:
                        os.remove(os.path.join("downloads", f))
                    except Exception:
                        pass
