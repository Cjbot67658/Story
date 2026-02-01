# main.py — safe, ready-to-run entrypoint
import os
from pyrogram import Client
from pymongo import MongoClient
from handlers import register_all_handlers

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "storybot")

def get_db():
    if not MONGO_URI:
        return None
    try:
        mc = MongoClient(MONGO_URI)
        return mc[DB_NAME]
    except Exception as e:
        # if DB fails, return None and let handlers handle it gracefully
        print("Warning: could not connect to MongoDB:", e)
        return None

def run_bot():
    db = get_db()
    app = Client("storybot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

    # register handlers (make sure handlers.register_all_handlers exists)
    register_all_handlers(app, db)

    # start the client (blocks)
    app.run()

if __name__ == "__main__":
    run_bot()
