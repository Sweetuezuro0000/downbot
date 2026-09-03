import os
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB Connection Setup
MONGO_URI = os.environ.get("MONGO_URI", "")
client = AsyncIOMotorClient(MONGO_URI)
db = client["downbot_db"]

users_col = db["users"]
settings_col = db["settings"]

# --- Settings Management ---

async def get_settings():
    settings = await settings_col.find_one({"_id": "config"})
    if not settings:
        default_settings = {
            "_id": "config",
            "limit_system_active": True,
            "maintenance_mode": False,
            "daily_free_limit": 5,
            "channel_link": os.environ.get("DEFAULT_CHANNEL_LINK", "https://t.me/YourChannel"),
            "ad_caption": "\n\n🚀 **Join Channel:** {channel_link}"
        }
        await settings_col.insert_one(default_settings)
        return default_settings
    return settings

async def update_settings(data: dict):
    await settings_col.update_one({"_id": "config"}, {"$set": data}, upsert=True)

# --- User Management ---

async def get_user(user_id: int):
    return await users_col.find_one({"user_id": user_id})

async def add_user(user_id: int, referred_by: int = None):
    user = await get_user(user_id)
    if not user:
        user_data = {
            "user_id": user_id,
            "joined_date": datetime.utcnow(),
            "is_premium": False,
            "premium_expiry": None,
            "is_banned": False,
            "referred_by": referred_by,
            "total_referrals": 0,
            "downloads_today": 0,
            "last_download_date": datetime.utcnow().strftime("%Y-%m-%d")
        }
        await users_col.insert_one(user_data)

        # Referral Count Reward Increment
        if referred_by and referred_by != user_id:
            await users_col.update_one(
                {"user_id": referred_by},
                {"$inc": {"total_referrals": 1}}
            )

# --- Daily Limit System ---

async def check_and_reset_limit(user_id: int):
    user = await get_user(user_id)
    if not user:
        return 0

    today = datetime.utcnow().strftime("%Y-%m-%d")
    last_date = user.get("last_download_date", "")

    # Daily Download Limit Auto-Reset Logic
    if last_date != today:
        await users_col.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "downloads_today": 0,
                    "last_download_date": today
                }
            }
        )
        return 0

    return user.get("downloads_today", 0)

async def increment_download_count(user_id: int):
    await users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"downloads_today": 1}}
    )

# --- Premium Access Management ---

async def add_premium_user(user_id: int, days: int):
    expiry_date = datetime.utcnow() + timedelta(days=days)
    await users_col.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "is_premium": True,
                "premium_expiry": expiry_date
            }
        },
        upsert=True
    )

async def remove_premium_user(user_id: int):
    await users_col.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "is_premium": False,
                "premium_expiry": None
            }
        }
    )

# --- Ban System Management ---

async def ban_user_db(user_id: int):
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"is_banned": True}},
        upsert=True
    )

async def unban_user_db(user_id: int):
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"is_banned": False}}
    )

async def is_user_banned(user_id: int) -> bool:
    user = await users_col.find_one({"user_id": user_id})
    if user:
        return user.get("is_banned", False)
    return False

# --- Database Statistics ---

async def get_db_stats():
    total_users = await users_col.count_documents({})
    premium_users = await users_col.count_documents({"is_premium": True})
    banned_users = await users_col.count_documents({"is_banned": True})
    return {
        "total": total_users,
        "premium": premium_users,
        "banned": banned_users
    }
