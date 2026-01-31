from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram import filters
from datetime import datetime
from pymongo import ReturnDocument

OWNER_IDS = []  # will be loaded from env in main or from db config

def register_admin_handlers(app, db):
    async def fantasy_cmd(client, message):
        if message.from_user.id not in OWNER_IDS:
            await message.reply_text("Only owners can use this.")
            return
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("+AddNEW", callback_data="ADMIN|ADDNEW|fantasy"),
                                   InlineKeyboardButton("+UpdateOLD", callback_data="ADMIN|UPDATE|fantasy")]])
        await message.reply_text("Admin panel: fantasy", reply_markup=kb)

    async def addnew_cb(client, cq):
        _, action, category = cq.data.split("|", 2)
        if cq.from_user.id not in OWNER_IDS:
            await cq.answer("Not allowed", show_alert=True); return
        # create session to add new story
        db.sessions.update_one({"_id": cq.from_user.id}, {"$set": {"step":"add_title","temp":{"category":category}}}, upsert=True)
        await cq.message.reply_text("Please send story title")
        await cq.answer()

    async def admin_messages(client, message):
        s = db.sessions.find_one({"_id": message.from_user.id})
        if not s: return
        step = s.get("step")
        temp = s.get("temp", {})
        if step == "add_title":
            db.sessions.update_one({"_id": message.from_user.id}, {"$set":{"step":"add_photo","temp.title":message.text}})
            await message.reply_text("Now send story photo")
        elif step == "add_photo" and message.photo:
            # store file_id
            file_id = (await message.photo[-1].get_file()).file_id if hasattr(message.photo[-1],'file_id') else message.photo[-1].file_id
            db.sessions.update_one({"_id": message.from_user.id}, {"$set":{"step":"add_desc","temp.photo_file_id":file_id}})
            await message.reply_text("Photo saved. Now send description")
        elif step == "add_desc":
            title = temp.get("title")
            photo = temp.get("photo_file_id")
            desc = message.text
            # atomically increment category count and create vision_id
            res = db.categories.find_one_and_update({"_id": temp['category']}, {"$inc":{"count":1}}, upsert=True, return_document=ReturnDocument.AFTER)
            code = res.get("code", temp['category'][:2])  # fallback
            vision = f"{code}{res['count']:02d}"
            story = {"category": temp['category'], "vision_id": vision, "title": title, "desc": desc, "photo_file_id": photo, "created_at": datetime.utcnow()}
            story_id = db.stories.insert_one(story).inserted_id
            # post to db channel if configured
            # clear session
            db.sessions.delete_one({"_id": message.from_user.id})
            await message.reply_text(f"Story added: {title} ({vision}). Now use +AddEP buttons to add episodes.")
        else:
            await message.reply_text("Unhandled admin step or invalid input.")
    app.add_handler(MessageHandler(fantasy_cmd, filters.private & filters.command("Fantasy")))
    app.add_handler(CallbackQueryHandler(addnew_cb, filters=filters.regex(r"^ADMIN\|ADDNEW\|")))
    app.add_handler(MessageHandler(admin_messages, filters.private & (filters.photo | filters.text)))
