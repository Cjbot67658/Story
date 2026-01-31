from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import parse_ep

def register_handlers(app, db):
    @app.on_message(filters.private & filters.command("start"))
    async def start_cmd(client, message):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Explore All", callback_data="MENU|EXPLORE")],
            [InlineKeyboardButton("Search", callback_data="MENU|SEARCH"),
             InlineKeyboardButton("Request & Comment", callback_data="MENU|REQUEST")]
        ])
        await message.reply_text("Welcome! Choose an option:", reply_markup=kb)

    @app.on_callback_query(filters.regex(r"^MENU\|"))
    async def menu_cb(client, cq):
        action = cq.data.split("|",1)[1]
        if action == "EXPLORE":
            cats = list(db.categories.find({}))
            if not cats:
                await cq.message.edit_text("No categories yet. Admins can add with /Fantasy etc.")
                await cq.answer()
                return
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{c.get('name','?')} ({c.get('count',0)})", callback_data=f"CAT|{c['_id']}")] for c in cats])
            await cq.message.edit_text("Choose category:", reply_markup=kb)
        elif action == "SEARCH":
            await cq.message.reply_text("Please send story name (recommended: any case).")
        elif action == "REQUEST":
            await cq.message.reply_text("Please send your message — it will be forwarded to owners.")
        await cq.answer()

    @app.on_callback_query(filters.regex(r"^CAT\|"))
    async def category_cb(client, cq):
        _, cat = cq.data.split("|",1)
        stories = list(db.stories.find({"category": cat}).sort("created_at", -1).limit(20))
        if not stories:
            await cq.answer("No stories in this category.")
            return
        for s in stories:
            caption = f"{s.get('title')}\n{(s.get('desc') or '')}\nVision: {s.get('vision_id')}"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Listen", callback_data=f"LISTEN|{s.get('vision_id')}")],
                [InlineKeyboardButton("← Back", callback_data="MENU|EXPLORE")]
            ])
            await client.send_photo(cq.from_user.id, s.get('photo_file_id'), caption=caption, reply_markup=kb)
        await cq.answer()

    @app.on_callback_query(filters.regex(r"^LISTEN\|"))
    async def listen_cb(client, cq):
        _, vision = cq.data.split("|",1)
        await client.send_message(cq.from_user.id, f"Plz send episode in format: Ep1 or Ep1-10 for {vision}")
        db.sessions.update_one({"_id": cq.from_user.id}, {"$set": {"expecting": "ep_for", "vision": vision}}, upsert=True)
        await cq.answer()

    @app.on_message(filters.private & filters.text & ~filters.command())
    async def text_handler(client, message):
        sess = db.sessions.find_one({"_id": message.from_user.id})
        text = message.text.strip()
        # If user is in listen flow
        if sess and sess.get("expecting") == "ep_for":
            ep = parse_ep(text)
            if not ep:
                await message.reply_text("Wrong format. Use Ep10 or Ep1-10 (case sensitive: 'Ep').")
                return
            start, end = ep
            story = db.stories.find_one({"vision_id": sess.get("vision")})
            if not story:
                await message.reply_text("Story not found.")
                db.sessions.delete_one({"_id": message.from_user.id})
                return
            episodes = list(db.episodes.find({"story_id": story["_id"], "ep_number": {"$gte": start, "$lte": end}}).sort("ep_number",1))
            if not episodes:
                await message.reply_text("No episodes saved for that range.")
                db.sessions.delete_one({"_id": message.from_user.id})
                return
            for e in episodes:
                await message.reply_text(f"Ep{e['ep_number']}: {e['link']}")
            db.sessions.delete_one({"_id": message.from_user.id})
            return
        # Default: treat as search query
        # Simple case-insensitive search on title
        cur = db.stories.find_one({"title_upper": text.upper()})
        if cur:
            caption = f"{cur.get('title')}\n{cur.get('desc')}\nVision: {cur.get('vision_id')}"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Listen", callback_data=f"LISTEN|{cur.get('vision_id')}")]])
            await client.send_photo(message.from_user.id, cur.get('photo_file_id'), caption=caption, reply_markup=kb)
        else:
            await message.reply_text("This story is not available. Use Request & Comment to notify the owner.")
