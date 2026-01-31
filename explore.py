from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_explore_handlers(app, db):
    async def start_cmd(client, message):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Explore All", callback_data="MENU|EXPLORE")],
            [InlineKeyboardButton("Search", callback_data="MENU|SEARCH"),
             InlineKeyboardButton("Request & Comment", callback_data="MENU|REQUEST")]
        ])
        await message.reply_text("Welcome! Choose an option:", reply_markup=kb)

    async def explore_cb(client, callback_query):
        # list categories from db
        categories = list(db.categories.find({}))
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{c['name']} ({c.get('count',0)})", callback_data=f"CATEGORY|{c['_id']}")] for c in categories])
        await callback_query.message.edit_text("Choose category:", reply_markup=kb)

    async def category_cb(client, callback_query):
        _, cat = callback_query.data.split("|", 1)
        stories = list(db.stories.find({"category": cat}).sort("created_at", -1).limit(20))
        if not stories:
            await callback_query.answer("No stories yet in this category.")
            return
        # send each story as photo + caption
        for s in stories:
            caption = f"{s['title']}\n{(s.get('desc') or '')}\nVision: {s['vision_id']}"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Listen", callback_data=f"LISTEN|{s['vision_id']}")],
                                       [InlineKeyboardButton("← Back", callback_data="MENU|EXPLORE")]])
            await client.send_photo(callback_query.from_user.id, s['photo_file_id'], caption=caption, reply_markup=kb)
        await callback_query.answer()

    app.add_handler(CallbackQueryHandler(explore_cb, filters=filters.regex(r"^MENU\|EXPLORE$")))
    app.add_handler(CallbackQueryHandler(category_cb, filters=filters.regex(r"^CATEGORY\|")))
    app.add_handler(MessageHandler(start_cmd, filters.private & filters.command("start")))
