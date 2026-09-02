import os

API_ID = int(os.environ.get("API_ID", "12345678"))          # my.telegram.org
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")      # my.telegram.org
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")  # @BotFather

# MongoDB URI (Cloud Atlas Connection String)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://username:password@cluster.mongodb.net/myDatabase")

# Admin Telegram User IDs (List of Integers)
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "123456789").split()]

# Default Settings (Agar DB mein na miley)
DEFAULT_FORCE_SUB = os.environ.get("DEFAULT_FORCE_SUB", "@YourChannelUsername")
DEFAULT_CHANNEL_LINK = os.environ.get("DEFAULT_CHANNEL_LINK", "https://t.me/YourChannelUsername")
