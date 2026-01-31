import re
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram import filters
from ..utils import EP_RE

def register_listen_handlers(app, db):
    async def listen_cb(client, callback_query):
        # ask for Ep format
        _, vision = callback_query.data.split("|",1)
        await callback_query.message.reply_text(f"Plz send episode in format: Ep1 or Ep1-10 for {vision}")
        # create a temporary session to expect episode (simple example)
        db.sessions.update_one({"_id": callback_query.from_user.id}, {"$set": {"expecting": "ep_for", "vision": vision}}, upsert=True)
        await callback_query.answer()

    async def message_ep(client, message):
        s = db.sessions.find_one({"_id": message.from_user.id})
        if not s or s.get("expecting") != "ep_for":
            return  # not in listen flow
        m = EP_RE.match(message.text or "")
        if not m:
            await message.reply_text("Wrong format. Use Ep10 or Ep1-10 (case sensitive: 'Ep').")
            return
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        # find story and episodes by vision
        story = db.stories.find_one({"vision_id": s['vision']})
        if not story:
            await message.reply_text("Story not found.")
            return
        # fetch episodes
        episodes = list(db.episodes.find({"story_id": story['_id'], "ep_number": {"$gte": start, "$lte": end}}).sort("ep_number",1))
        if not episodes:
            await message.reply_text("No episodes saved for that range.")
            return
        for ep in episodes:
            # send the link (or forward to redirect bot etc)
            await message.reply_text(f"Ep{ep['ep_number']}: {ep['link']}")
        # clear session
        db.sessions.delete_one({"_id": message.from_user.id})

    app.add_handler(CallbackQueryHandler(listen_cb, filters=filters.regex(r"^LISTEN\|")))
    app.add_handler(MessageHandler(message_ep, filters.private & filters.text & ~filters.command()))
