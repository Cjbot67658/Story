from pyrogram import Client
from pymongo import MongoClient
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI

app = Client(
    "broadcast_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

mongo = MongoClient(MONGO_URI)
db = mongo["broadcast_bot"]
users = db["users"]

@app.on_message()
async def save_user(client, message):
    if message.from_user:
        user_id = message.from_user.id
        if not users.find_one({"_id": user_id}):
            users.insert_one({"_id": user_id})
        await message.reply("User saved ✅")

app.run()
