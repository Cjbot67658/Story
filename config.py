import os

# Read from environment variables, with safe defaults for local dev
API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_URI = os.environ.get("DATABASE_URL", "")
DB_NAME = os.environ.get("DATABASE_NAME", "Cluster0")
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip()]
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID", ""))
API_ID = int(os.getenv("API_ID", "27857521"))
API_HASH = os.getenv("API_HASH", "627b314d25c83e2c9a1a99db9ae0a3ef")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8317617574:AAFQZD6lGCEtK2oIf_qNSDpe_zpqKYAugyQ")
DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://alpmanas56_db_user:njoXL0eSLLVsE5rH@cluster0.fi3wrdi.mongodb.net/?appName=Cluster0")
MONGO_URI = DB_URI
DB_NAME = os.environ.get("DATABASE_NAME", "Cluster0")
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "7024087501").split(",") if x.strip()]
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID", "-1002342989997"))
