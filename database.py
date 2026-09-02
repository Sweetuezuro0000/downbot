import motor.motor_asyncio
import datetime
from config import MONGO_URI, DEFAULT_FORCE_SUB, DEFAULT_CHANNEL_LINK

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["downloader_bot_db"]

users_col = db["users"]
settings_col = db["settings"]

# --- SETTINGS MANAGEMENT ---
async def get_settings():
    settings = await settings_col.find_one({"id": "config"})
    if not settings:
        default = {
            "id": "config",
            "limit_system_active": False,  # Default OFF as requested
            "daily_free_limit": 5,
            "premium_mode_active": False,
            "maintenance_mode": False,
            "force_sub_channel": DEFAULT_FORCE_SUB,
            "channel_link": DEFAULT_CHANNEL_LINK,
            "ad_caption": "\n\n👉 Join: {channel_link}"
        }
        await settings_col.insert_one(default)
        return default
    return settings

async def update_setting(key, value):
    await settings_col.update_one({"id": "config"}, {"$set": {key: value}}, upsert=True)

# --- USER MANAGEMENT ---
async def get_user(user_id: int):
    return await users_col.find_one({"user_id": user_id})

async def add_user(user_id: int, referred_by: int = None):
    user = await get_user(user_id)
    if not user:
        new_user = {
            "user_id": user_id,
            "joined_date": datetime.datetime.utcnow(),
            "downloads_today": 0,
            "last_download_date": datetime.date.today().isoformat(),
            "is_premium": False,
            "referred_by": referred_by,
            "total_referrals": 0,
            "is_banned": False
        }
        await users_col.insert_one(new_user)
        
        # Credit Referral
        if referred_by and referred_by != user_id:
            await users_col.update_one({"user_id": referred_by}, {"$inc": {"total_referrals": 1}})

async def check_and_reset_limit(user_id: int):
    user = await get_user(user_id)
    if not user:
        return 0
    today = datetime.date.today().isoformat()
    if user.get("last_download_date") != today:
        await users_col.update_one(
            {"user_id": user_id},
            {"$set": {"downloads_today": 0, "last_download_date": today}}
        )
        return 0
    return user.get("downloads_today", 0)

async def increment_download_count(user_id: int):
    await users_col.update_one({"user_id": user_id}, {"$inc": {"downloads_today": 1}})

async def get_stats():
    total_users = await users_col.count_documents({})
    banned_users = await users_col.count_documents({"is_banned": True})
    premium_users = await users_col.count_documents({"is_premium": True})
    return total_users, banned_users, premium_users
