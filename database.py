from datetime import datetime, timedelta

# --- Premium Management ---

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

# --- Ban Management ---

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

# --- Analytics ---

async def get_db_stats():
    total_users = await users_col.count_documents({})
    premium_users = await users_col.count_documents({"is_premium": True})
    banned_users = await users_col.count_documents({"is_banned": True})
    return {
        "total": total_users,
        "premium": premium_users,
        "banned": banned_users
    }
