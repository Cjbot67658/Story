import os
from pyrogram import Client
from pymongo import MongoClient
from handlers import register_all_handlers

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
