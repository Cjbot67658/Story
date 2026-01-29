import os

# Read from environment variables, with safe defaults for local dev
API_ID = int(os.getenv("API_ID", "27857521"))
API_HASH = os.getenv("API_HASH", "627b314d25c83e2c9a1a99db9ae0a3ef")
BOT_TOKEN = os.getenv("BOT_TOKEN", "123456:ABC-DEF...")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://alpmanas56_db_user:njoXL0eSLLVsE5rH@cluster0.fi3wrdi.mongodb.net/?appName=Cluster0")
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "7024087501").split(",") if x.strip()]
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID", "-1001234567890"))

