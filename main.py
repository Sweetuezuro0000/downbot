import os
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN
from database import add_user
from modules.admin import register_admin_handlers
from modules.referral import register_referral_handlers
from modules.downloader import register_downloader_handlers

# ==========================================
# 1. FLASK WEB SERVER (Render Port Detection Fix)
# ==========================================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Live and Healthy!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    # 0.0.0.0 bind hona Render ke liye mandatory hai
    web_app.run(host="0.0.0.0", port=port)

# ==========================================
# 2. PYROGRAM BOT SETUP
# ==========================================
app = Client(
    "downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    referred_by = None

    # Extract referral code
    if len(message.command) > 1 and message.command[1].startswith("ref_"):
        try:
            referred_by = int(message.command[1].split("_")[1])
        except Exception:
            pass

    await add_user(user_id, referred_by)

    await message.reply_text(
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        "I'm an **All-In-One Downloader Bot**!\n\n"
        "Send 📹 Instagram Reels, YouTube Shorts, TikTok, Pinterest links to download instant video/audio/post.\n\n"
        "Developer @parawebdev"
    )

# Register All Modules
register_admin_handlers(app)
register_referral_handlers(app)
register_downloader_handlers(app)

# ==========================================
# 3. EXECUTION
# ==========================================
if __name__ == "__main__":
    # Web server ko background thread me pehle start karein
    threading.Thread(target=run_web, daemon=True).start()
    
    print("🚀 All-In-One Downloader Bot with Web Server Started!")
    app.run()
