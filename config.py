import os

# Read from environment variables, with safe defaults for local dev
API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN", "123456:ABC-DEF...")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://username:password@cluster0.mongodb.net/storybot?retryWrites=true&w=majority")
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "111111111").split(",") if x.strip()]
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID", "-1001234567890"))

