# bot.py — cleaned, dynamic categories, Pocket-FM style defaults
import os
import time
import logging
import re

from pymongo import MongoClient, ReturnDocument
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ----------------- CONFIG (use env vars; defaults are placeholders) -----------------
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "123456:ABC-DEF")
MONGO_URI = os.environ.get("MONGO_URI", "")  # set on Koyeb; locally use non-SRV if needed
DB_NAME = os.environ.get("DB_NAME", None)
OWNER_IDS = [int(x) for x in os.environ.get("OWNER_IDS", "111111111").split(",") if x.strip()]
DB_CHANNEL_ID = int(os.environ.get("DB_CHANNEL_ID", "-1001234567890"))
# ------------------------------------------------------------------------------------

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Regex for Ep format (case-sensitive: 'Ep' exactly)
EP_RE = re.compile(r"^Ep(\d+)(?:-(\d+))?$")

# Initialize MongoDB client once (best-effort; may run without DB)
mc = None
db = None
try:
    if MONGO_URI:
        mc = MongoClient(MONGO_URI)
        db = mc[DB_NAME] if DB_NAME else mc.get_database()
        logger.info("Connected to MongoDB")
    else:
        logger.warning("MONGO_URI not set; running without DB (local test mode)")
except Exception as e:
    logger.exception("MongoDB connection failed: %s", e)
    mc = None
    db = None

# If DB present, set collections; else None
cats_col = db["categories"] if db else None
stories_col = db["stories"] if db else None
users_col = db["users"] if db else None
sessions_col = db["sessions"] if db else None

# Create a factory for the Client (but do NOT start it here)
def create_client(session_name: str = "storybot"):
    return Client(session_name, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# -------------------------
# Helpers
# -------------------------
def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Explore All", callback_data="MENU|EXPLORE")],
        [InlineKeyboardButton("Search", callback_data="MENU|SEARCH"),
         InlineKeyboardButton("Request & Comment", callback_data="MENU|REQUEST")]
    ])

def back_kb(payload="MENU|MAIN"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data=payload)]])

def ensure_default_categories():
    """
    Seed a larger, Pocket-FM style defaults list (only inserts if not present).
    """
    if not cats_col:
        return

    defaults = [
        {"_id": "fantasy", "name": "Fantasy", "prefix": "fa", "count": 0},
        {"_id": "romance", "name": "Romance", "prefix": "ro", "count": 0},
        {"_id": "thriller", "name": "Thriller", "prefix": "th", "count": 0},
        {"_id": "horror", "name": "Horror", "prefix": "ho", "count": 0},
        {"_id": "mystery", "name": "Mystery", "prefix": "my", "count": 0},
        {"_id": "sifi", "name": "Sci-Fi", "prefix": "si", "count": 0},
        {"_id": "drama", "name": "Drama", "prefix": "dr", "count": 0},
        {"_id": "action", "name": "Action", "prefix": "ac", "count": 0},
        {"_id": "comedy", "name": "Comedy", "prefix": "co", "count": 0},
        {"_id": "mythology", "name": "Mythology", "prefix": "mi", "count": 0},
        {"_id": "inspirational", "name": "Inspirational", "prefix": "in", "count": 0},
        {"_id": "crime", "name": "Crime", "prefix": "cr", "count": 0},
        {"_id": "suspense", "name": "Suspense", "prefix": "su", "count": 0},
        {"_id": "family", "name": "Family", "prefix": "fa2", "count": 0},
        {"_id": "devotional", "name": "Devotional", "prefix": "de", "count": 0},
        {"_id": "education", "name": "Education", "prefix": "ed", "count": 0},
        {"_id": "biography", "name": "Biography", "prefix": "bi", "count": 0},
        {"_id": "historical", "name": "Historical", "prefix": "hi", "count": 0},
    ]

    for d in defaults:
        try:
            cats_col.update_one({"_id": d["_id"]}, {"$setOnInsert": d}, upsert=True)
        except Exception:
            logger.exception("Failed ensure_default_categories for %s", d["_id"])

# -------------------------
# Register handlers
# -------------------------
def register_all_handlers(app: Client, db_handle):
    """
    Register all handlers on the provided pyrogram Client 'app'.
    This allows main.py to create the client and call this function
    before starting the client.
    """
    # ensure collections reference from passed db_handle if provided
    global cats_col, stories_col, users_col, sessions_col
    if db_handle:
        try:
            cats_col = db_handle["categories"]
            stories_col = db_handle["stories"]
            users_col = db_handle["users"]
            sessions_col = db_handle["sessions"]
        except Exception:
            logger.exception("Failed to assign collections from db_handle; continuing with previous values")

    ensure_default_categories()

    # --- simple test handler ---
    @app.on_message(filters.private & filters.command("test"))
    async def _test_handler(client, message):
        await message.reply_text("✅ Bot alive hai bhai")

    # --- start ---
    @app.on_message(filters.private & filters.command("start"))
    async def start_cmd(client, message):
        if users_col:
            try:
                users_col.update_one({"_id": message.from_user.id}, {"$set": {"_id": message.from_user.id}}, upsert=True)
            except Exception:
                logger.exception("Failed to update user in DB")
        await message.reply_text("Welcome! Choose an option:", reply_markup=main_menu_kb())

    # --- broadcast (owner only) ---
    @app.on_message(filters.private & filters.command("broadcast"))
    async def broadcast_cmd(client, message):
        if not message.from_user or not is_owner(message.from_user.id):
            await message.reply_text("Only owners can use this.")
            return
        if not message.reply_to_message:
            await message.reply_text("Reply to a message to broadcast.")
            return
        sent = 0
        failed = 0
        await message.reply_text("Broadcast started... (may take time)")
        if not users_col:
            await message.reply_text("No user DB configured.")
            return
        for u in users_col.find({}, {"_id": 1}):
            uid = u["_id"]
            try:
                await message.reply_to_message.copy(uid)
                sent += 1
                time.sleep(0.06)
            except Exception as e:
                failed += 1
                logger.warning(f"Broadcast failed to {uid}: {e}")
        await message.reply_text(f"Broadcast finished. Sent: {sent}, Failed: {failed}")

    # --- dynamic admin panel handler (handles ALL categories present in DB) ---
    @app.on_message(filters.private & filters.text)
    async def dynamic_admin_panel(client, message):
        # only owners can open admin panels via /command
        if not message.from_user or not is_owner(message.from_user.id):
            return

        text = (message.text or "").strip()
        # only handle starting slash commands like /Fantasy or /fantasy@BotName
        if not text.startswith("/"):
            return

        # extract command name (without leading / and botusername)
        cmd = text.split()[0][1:].split("@")[0].lower()

        # Try _id match, then name case-insensitive, then alias (if you add)
        cat_doc = None
        if cats_col:
            try:
                cat_doc = cats_col.find_one({"_id": cmd})
                if not cat_doc:
                    cat_doc = cats_col.find_one({"name": {"$regex": f"^{re.escape(cmd)}$", "$options": "i"}})
                # optional: check 'aliases' array if you add it to docs
                if not cat_doc:
                    cat_doc = cats_col.find_one({"aliases": {"$in": [cmd]}})
            except Exception:
                logger.exception("Error querying categories collection")

        if not cat_doc:
            # Not a known category command — ignore and let other handlers process
            return

        cat_id = cat_doc["_id"]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("+AddNEW", callback_data=f"ADMIN|ADDNEW|{cat_id}")],
            [InlineKeyboardButton("+UpdateOLD", callback_data=f"ADMIN|UPDATE|{cat_id}")],
            [InlineKeyboardButton("← Back", callback_data="MENU|MAIN")]
        ])
        await message.reply_text(f"Admin panel — {cat_doc['name']}", reply_markup=kb)

    # --- callback handlers (note: escape the pipe in regex) ---
    @app.on_callback_query(filters.regex(r"^MENU\|"))
    async def menu_cb(client, cbq):
        action = cbq.data.split("|", 1)[1]
        if action == "EXPLORE":
            buttons = []
            if cats_col:
                for cat in cats_col.find():
                    cnt = cat.get("count", 0)
                    buttons.append([InlineKeyboardButton(f"{cat['name']} ({cnt})", callback_data=f"CAT|{cat['_id']}")])
            buttons.append([InlineKeyboardButton("← Back", callback_data="MENU|MAIN")])
            await cbq.message.edit_text("Choose a category:", reply_markup=InlineKeyboardMarkup(buttons))
        elif action == "SEARCH":
            await cbq.message.reply_text("Send story title in CAPITAL LETTERS (EXACT).", reply_markup=back_kb("MENU|MAIN"))
        elif action == "REQUEST":
            await cbq.message.reply_text("Send your message and it will be forwarded to the owner.", reply_markup=back_kb("MENU|MAIN"))
        elif action == "MAIN":
            await cbq.message.edit_text("Main menu:", reply_markup=main_menu_kb())
        else:
            await cbq.answer("Unknown menu action.")

    @app.on_callback_query(filters.regex(r"^CAT\|"))
    async def cat_open_cb(client, cbq):
        cat_id = cbq.data.split("|", 1)[1]
        docs = list(stories_col.find({"category": cat_id})) if stories_col else []
        if not docs:
            await cbq.message.reply_text("No stories yet in this category.", reply_markup=back_kb("MENU|EXPLORE"))
            return
        for s in docs:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Listen", callback_data=f"LISTEN|{s['vision_id']}")]])
            try:
                await cbq.message.reply_photo(s["photo_file_id"], caption=f"{s['title']}\n\n{s['desc']}", reply_markup=kb)
            except Exception:
                await cbq.message.reply_text(f"{s['title']}\n\n{s['desc']}", reply_markup=kb)
        await cbq.message.reply_text("End of list.", reply_markup=back_kb("MENU|EXPLORE"))

    @app.on_callback_query(filters.regex(r"^LISTEN\|"))
    async def listen_cb(client, cbq):
        vision_id = cbq.data.split("|", 1)[1]
        if users_col:
            users_col.update_one({"_id": cbq.from_user.id}, {"$set": {"last_story": vision_id}}, upsert=True)
        await cbq.message.reply_text(f"You chose {vision_id}. Please send episode in format: Ep10 or Ep1-50 (case-sensitive 'Ep').", reply_markup=back_kb("MENU|MAIN"))

    # --- text handler for non-commands (safe) ---
    @app.on_message(filters.private & filters.text)
    async def text_handler(client, message):
        text = (message.text or "").strip()
        if not text:
            return
        # ignore obvious commands (they are handled elsewhere)
        if text[0] in ("/", "!", "."):
            return

        # ep format
        if EP_RE.match(text):
            u = users_col.find_one({"_id": message.from_user.id}) if users_col else None
            if not u or "last_story" not in u:
                await message.reply_text("Choose a story first (Explore -> choose story -> Listen).")
                return
            vision = u["last_story"]
            st = stories_col.find_one({"vision_id": vision}) if stories_col else None
            if not st:
                await message.reply_text("Story data not found.")
                return
            for ep in st.get("episodes", []):
                if ep.get("ep") == text:
                    await message.reply_text(ep.get("link"))
                    return
            await message.reply_text("Episode link not available for this selection.")
            return

        # caps search
        if text.isupper():
            s = stories_col.find_one({"title": text}) if stories_col else None
            if not s:
                await message.reply_text("Story not available. Use Request & Comment to ask owner.", reply_markup=back_kb("MENU|MAIN"))
                return
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Listen", callback_data=f"LISTEN|{s['vision_id']}")]])
            try:
                await message.reply_photo(s["photo_file_id"], caption=f"{s['title']}\n\n{s['desc']}", reply_markup=kb)
            except Exception:
                await message.reply_text(f"{s['title']}\n\n{s['desc']}", reply_markup=kb)
            return

        # else forward as request/comment to owners
        if not message.entities:
            for oid in OWNER_IDS:
                try:
                    await message.forward(oid)
                except Exception as e:
                    logger.warning(f"Failed to forward user request to {oid}: {e}")
            await message.reply_text("Your message was forwarded to the admin. Thank you!", reply_markup=back_kb("MENU|MAIN"))
            return

    # --- admin callbacks placeholder ---
    @app.on_callback_query(filters.regex(r"^ADMIN\|"))
    async def admin_cb(client, cbq):
        parts = cbq.data.split("|")
        action = parts[1]
        cat = parts[2] if len(parts) > 2 else None
        if action == "ADDNEW":
            if sessions_col:
                sessions_col.update_one({"_id": cbq.from_user.id}, {"$set": {"mode": "addnew", "cat": cat, "stage": "await_title"}}, upsert=True)
            await cbq.message.reply_text("🔹 AddNEW: Send story TITLE (plain text).", reply_markup=back_kb("MENU|MAIN"))
        elif action == "UPDATE":
            if sessions_col:
                sessions_col.update_one({"_id": cbq.from_user.id}, {"$set": {"mode": "update", "cat": cat, "stage": "await_vision"}}, upsert=True)
            await cbq.message.reply_text("🔹 UpdateOLD: Send VISION ID (e.g., fa01).", reply_markup=back_kb("MENU|MAIN"))
        else:
            await cbq.answer("Unknown admin action.")

    # registration finished
    logger.info("Handlers registered on app")

# -------------------------
# convenience: run directly
# -------------------------
def run_bot():
    db_handle = None
    if MONGO_URI:
        try:
            mc_local = MongoClient(MONGO_URI)
            db_handle = mc_local[DB_NAME] if DB_NAME else mc_local.get_database()
        except Exception:
            logger.exception("run_bot: failed to connect to MongoDB; running without DB")
            db_handle = None

    app = create_client()
    register_all_handlers(app, db_handle)
    logger.info("Starting Pyrogram client...")
    app.run()

# If run directly (for local testing)
if __name__ == "__main__":
    try:
        run_bot()
    except Exception:
        logger.exception("Bot crashed on direct run")
