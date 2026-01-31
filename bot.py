"""
StoryBot - single-file Telegram bot

Features:
- /start main menu: Explore All | Search | Request & Comment
- Admin commands: /Fantasy /Love /Sifi (open admin panel for that category)
- Admin flows: +AddNEW (title -> photo -> desc -> auto vision id) and +UpdateOLD
- Episode add: +AddEP... buttons (admin provides manual link)
- Listen: user chooses story -> clicks Listen -> sends Ep format (Ep10 or Ep1-10) and bot returns saved link
- Search: user sends story name in CAPITAL letters (strict check)
- Request & Comment: user message forwarded to OWNER_IDS
- Broadcast: admin replies to a message and runs /broadcast to send that message to all users
- DB: MongoDB collections: categories, stories, users, sessions
- Posts new story (photo+caption) to a DB channel (DB_CHANNEL_ID)
"""

# bot.py (combined single-file entrypoint)
import os
import logging
import time
import re

from pymongo import MongoClient, ReturnDocument
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ----------------- CONFIG: use environment variables with safe defaults -----------------
API_ID = int(os.environ.get("API_ID", "123456"))                # from my.telegram.org
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")         # from my.telegram.org
BOT_TOKEN = os.environ.get("BOT_TOKEN", "123456:ABC-DEF...")   # Bot token from BotFather

# NOTE: prefer setting MONGO_URI as an env var on your host (Koyeb/Railway).
# For Termux local testing you may need the non-SRV (mongodb://...) form — see notes below.
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://Profiledata:dhbh5fgnnk8ygvhnj7@cluster0.fi3wrdi.mongodb.net/?appName=Cluster0"
)

OWNER_IDS = [int(x) for x in os.environ.get("OWNER_IDS", "111111111").split(",") if x.strip()]
DB_CHANNEL_ID = int(os.environ.get("DB_CHANNEL_ID", "-1001234567890"))

# -----------------------------------------------------------------------------------------

# Configure logging (adjust level if you want more/less logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize MongoDB client and database handle
mc = None
db = None
try:
    if MONGO_URI:
        mc = MongoClient(MONGO_URI)
        # If you want a specific database name, either parse from URI or set here:
        # db = mc.get_database("your_db_name")
        # For Atlas default you might want to set a DB name via env var:
        DB_NAME = os.environ.get("DB_NAME", None)
        if DB_NAME:
            db = mc[DB_NAME]
        else:
            # fallback to 'test' or the default database from URI
            db = mc.get_database()
        logger.info("Connected to MongoDB")
except Exception as e:
    logger.warning(f"Could not connect to MongoDB at startup: {e}")
    # keep db = None; handlers should handle missing DB gracefully

# Create Pyrogram client
app = Client("storybot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# -------------------------
# Example handlers (minimal)
# You may already have handlers in a separate module; if so, call register_handlers(app, db) instead.
# The following are small example handlers so this file is runnable out-of-the-box.
# Replace / extend with your real handlers or keep them in separate files and import/register.
# -------------------------

@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("Hello — bot is up and running!")

@app.on_message(filters.private & filters.command("broadcast"))
async def broadcast_cmd(client, message):
    # placeholder: owner-only broadcast
    if message.from_user and message.from_user.id in OWNER_IDS:
        await message.reply_text("Broadcast command received. (implement your logic)")
    else:
        await message.reply_text("You are not authorized to run broadcast.")

# Handle plain text messages that are NOT commands:
@app.on_message(filters.private & filters.text & ~filters.command())
async def text_handler(client, message):
    text = message.text or ""
    # ignore messages starting with typical command characters (double-safety)
    if text.startswith(("/", "!", ".")):
        return
    # Example reply
    await message.reply_text(f"You said: {text}")

# Add more handlers as needed...
# e.g. @app.on_message(filters.private & filters.command(["Fantasy", "Sifi", "Love"]))


# -------------------------
# run_bot() function to be imported by web_and_bot.py
# -------------------------
def run_bot():
    """
    Register any external handlers here (if you keep them in other modules),
    then start the Pyrogram client. This function is safe to import.
    """
    # If you use a handlers module: from handlers import register_handlers; register_handlers(app, db)
    # Example:
    # try:
    #     from handlers import register_handlers
    #     register_handlers(app, db)
    # except Exception:
    #     logger.info("No external handlers found; running built-in handlers.")

    logger.info("Starting Pyrogram client...")
    app.run()


if __name__ == "__main__":
    # Running directly: start the bot (useful for local dev)
    try:
        run_bot()
    except Exception as exc:
        logger.exception("Bot crashed: %s", exc)

# Regex for Ep format (case-sensitive: 'Ep' exactly)
EP_RE = re.compile(r"^Ep(\d+)(?:-(\d+))?$")

# Initialize
app = Client("storybot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mc = MongoClient(MONGO_URI)
db = mc["storybot"]
cats_col = db["categories"]
stories_col = db["stories"]
users_col = db["users"]
sessions_col = db["sessions"]   # temporary admin/session states

# Helper: check admin
def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS

# Helper: main menu keyboard
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Explore All", callback_data="MENU|EXPLORE")],
        [InlineKeyboardButton("Search", callback_data="MENU|SEARCH"),
         InlineKeyboardButton("Request & Comment", callback_data="MENU|REQUEST")]
    ])

# Helper: back button
def back_kb(payload="MENU|MAIN"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data=payload)]])

# On /start
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    users_col.update_one({"_id": message.from_user.id}, {"$set": {"_id": message.from_user.id}}, upsert=True)
    await message.reply_text("Welcome! Choose an option:", reply_markup=main_menu_kb())

# ----------------- BROADCAST (admin) -----------------
# Usage: reply to a message with /broadcast
@app.on_message(filters.private & filters.command("broadcast"))
async def broadcast_cmd(client, message):
    if not is_owner(message.from_user.id):
        await message.reply_text("Only owners can use this.")
        return
    if not message.reply_to_message:
        await message.reply_text("Reply to a message to broadcast.")
        return

    sent = 0
    failed = 0
    await message.reply_text("Broadcast started... (may take time)")
    for u in users_col.find({}, {"_id": 1}):
        uid = u["_id"]
        try:
            # copy is safer (keeps original media), but here we use copy_to
            await message.reply_to_message.copy(uid)
            sent += 1
            time.sleep(0.06)  # small delay to avoid hitting rate limits
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast failed to {uid}: {e}")

    await message.reply_text(f"Broadcast finished. Sent: {sent}, Failed: {failed}")

# ----------------- ADMIN: create default categories if not present -----------------
def ensure_default_categories():
    defaults = [
        {"_id": "fantasy", "name": "Fantasy", "prefix": "fa", "count": 0},
        {"_id": "sifi", "name": "Sifi", "prefix": "si", "count": 0},
        {"_id": "love", "name": "Love", "prefix": "lo", "count": 0},
    ]
    for d in defaults:
        cats_col.update_one({"_id": d["_id"]}, {"$setOnInsert": d}, upsert=True)

# Run once on startup
ensure_default_categories()

# ----------------- MENU CALLBACKS -----------------
@app.on_callback_query(filters.regex(r"^MENU\|"))
async def menu_cb(client, cbq):
    action = cbq.data.split("|", 1)[1]
    if action == "EXPLORE":
        # show categories with counts
        buttons = []
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

# example in bot.py
def run_bot():
    # agar tum Pyrogram ya aiogram use kar rahe ho, call the start method here
    app.run()      # ya app.start(), app.start_polling(), client.run(), etc.

# ----------------- CATEGORY & STORY LISTING -----------------
@app.on_callback_query(filters.regex(r"^CAT\|"))
async def cat_open_cb(client, cbq):
    cat_id = cbq.data.split("|", 1)[1]
    # fetch stories in category -> show as individual photo messages + Listen button
    docs = list(stories_col.find({"category": cat_id}))
    if not docs:
        await cbq.message.reply_text("No stories yet in this category.", reply_markup=back_kb("MENU|EXPLORE"))
        return
    # Send each story as a photo message with Listen button
    for s in docs:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Listen", callback_data=f"LISTEN|{s['vision_id']}")]])
        # send photo (may be file_id)
        try:
            await cbq.message.reply_photo(s["photo_file_id"], caption=f"{s['title']}\n\n{s['desc']}", reply_markup=kb)
        except Exception:
            # fallback: send text if photo missing
            await cbq.message.reply_text(f"{s['title']}\n\n{s['desc']}", reply_markup=kb)
    # a back button to categories
    await cbq.message.reply_text("End of list.", reply_markup=back_kb("MENU|EXPLORE"))

# ----------------- LISTEN FLOW -----------------
@app.on_callback_query(filters.regex(r"^LISTEN\|"))
async def listen_cb(client, cbq):
    vision_id = cbq.data.split("|", 1)[1]
    users_col.update_one({"_id": cbq.from_user.id}, {"$set": {"last_story": vision_id}}, upsert=True)
    await cbq.message.reply_text(f"You chose {vision_id}. Please send episode in format: Ep10 or Ep1-50 (case-sensitive 'Ep').", reply_markup=back_kb("MENU|MAIN"))

@app.on_message(filters.private & filters.text)
def handle_message(client, message):
    text = message.text or ""
    # ignore messages that look like commands
    if text.startswith(("/", "!", ".")):
        return

    # proceed with non-command text handling...
async def ep_request_handler(client, message):
    text = message.text.strip()
    # If text matches Ep format exactly
    if EP_RE.match(text):
        u = users_col.find_one({"_id": message.from_user.id})
        if not u or "last_story" not in u:
            await message.reply_text("Choose a story first (Explore -> choose story -> Listen).")
            return
        vision = u["last_story"]
        st = stories_col.find_one({"vision_id": vision})
        if not st:
            await message.reply_text("Story data not found.")
            return
        # Look for exact ep or range stored
        ep_entry = None
        for ep in st.get("episodes", []):
            if ep.get("ep") == text:
                ep_entry = ep
                break
        if ep_entry:
            await message.reply_text(ep_entry.get("link"))
        else:
            await message.reply_text("Episode link not available for this selection.")
        return

    # If user sends UPPERCASE (likely a search)
    if text.isupper():
        # treat as search request
        s = stories_col.find_one({"title": text})
        if not s:
            await message.reply_text("Story not available. Use Request & Comment to ask owner.", reply_markup=back_kb("MENU|MAIN"))
            return
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Listen", callback_data=f"LISTEN|{s['vision_id']}")]])
        try:
            await message.reply_photo(s["photo_file_id"], caption=f"{s['title']}\n\n{s['desc']}", reply_markup=kb)
        except Exception:
            await message.reply_text(f"{s['title']}\n\n{s['desc']}", reply_markup=kb)
        return

    # If message is not Ep and not CAPS, it might be a request & comment
    # Forward to owners
    # (We only forward non-command, non-ep, non-caps messages to owner as user's request)
    if not message.entities and not message.text.startswith('/'):
        # forward as "request/comment"
        for oid in OWNER_IDS:
            try:
                await message.forward(oid)
            except Exception as e:
                logger.warning(f"Failed to forward user request to {oid}: {e}")
        await message.reply_text("Your message was forwarded to the admin. Thank you!", reply_markup=back_kb("MENU|MAIN"))
        return

# ----------------- ADMIN PANEL: category commands (/Fantasy etc) -----------------
@app.on_message(filters.private & filters.command(["Fantasy", "Sifi", "Love"]))
async def admin_panel_cmd(client, message):
    if not is_owner(message.from_user.id):
        await message.reply_text("Only owners can use this command.")
        return
    cmd = message.command[0].lower()  # "fantasy"
    cat_doc = cats_col.find_one({"_id": cmd})
    if not cat_doc:
        # create if missing
        cats_col.insert_one({"_id": cmd, "name": message.command[0], "prefix": cmd[:2], "count": 0})
        cat_doc = cats_col.find_one({"_id": cmd})
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("+AddNEW", callback_data=f"ADMIN|ADDNEW|{cmd}")],
        [InlineKeyboardButton("+UpdateOLD", callback_data=f"ADMIN|UPDATE|{cmd}")],
        [InlineKeyboardButton("← Back", callback_data="MENU|MAIN")]
    ])
    await message.reply_text(f"Admin panel — {cat_doc['name']}", reply_markup=kb)

# ----------------- ADMIN CALLBACKS -----------------
@app.on_callback_query(filters.regex(r"^ADMIN\|"))
async def admin_cb(client, cbq):
    parts = cbq.data.split("|")
    action = parts[1]
    cat = parts[2] if len(parts) > 2 else None

    if action == "ADDNEW":
        # set session for this admin to collect title->photo->desc
        sessions_col.update_one({"_id": cbq.from_user.id}, {"$set": {"mode": "addnew", "cat": cat, "stage": "await_title"}}, upsert=True)
        await cbq.message.reply_text("🔹 AddNEW: Send story TITLE (plain text).", reply_markup=back_kb("MENU|MAIN"))

    elif action == "UPDATE":
        # ask for vision id to update
        sessions_col.update_one({"_id": cbq.from_user.id}, {"$set": {"mode": "update", "cat": cat, "stage": "await_vision"}}, upsert=True)
        await cbq.message.reply_text("🔹 UpdateOLD: Send VISION ID (e.g., fa01).", reply_markup=back_kb("MENU|MAIN"))

    else:
        await cbq.answer("Unknown admin action.")

# ----------------- ADMIN MESSAGES: title, photo, desc, episode link flows -----------------
# Title handler (admin)
@app.on_message(filters.private & filters.text & ~filters.command(["start", "help"]))
async def title_handler(client, message):
    # message here is guaranteed to be text and NOT the listed commands
    text = message.text or ""
    # your logic here
async def admin_texts(client, message):
    s = sessions_col.find_one({"_id": message.from_user.id})
    # No session -> might be normal user flows (handled earlier)
    if not s:
        return

    mode = s.get("mode")
    stage = s.get("stage")

    # Cancel/back: if user sends "← Back" text (or /cancel) we clear
    if message.text.strip().lower() in ["/cancel", "cancel", "back", "← back", "←"]:
        sessions_col.delete_one({"_id": message.from_user.id})
        await message.reply_text("Operation cancelled.", reply_markup=main_menu_kb())
        return

    # ADDNEW flow
    if mode == "addnew":
        if stage == "await_title":
            # save title and ask for photo
            sessions_col.update_one({"_id": message.from_user.id}, {"$set": {"title": message.text.strip(), "stage": "await_photo"}}, upsert=True)
            await message.reply_text("Title saved. Now send story PHOTO (as an image).", reply_markup=back_kb("MENU|MAIN"))
            return
        elif stage == "await_desc":
            # finalize story creation
            desc = message.text.strip()
            sess = sessions_col.find_one({"_id": message.from_user.id})
            title = sess.get("title")
            photo_file_id = sess.get("photo_file_id")
            cat = sess.get("cat")
            if not (title and photo_file_id):
                await message.reply_text("Missing data. Start again with +AddNEW.", reply_markup=back_kb("MENU|MAIN"))
                sessions_col.delete_one({"_id": message.from_user.id})
                return

            # atomically increment category count and generate vision id
            new_cat = cats_col.find_one_and_update({"_id": cat}, {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER)
            count = new_cat.get("count", 0)
            prefix = new_cat.get("prefix", cat[:2])
            vision_id = f"{prefix}{str(count).zfill(2)}"  # fa01, lo01, etc

            # insert story doc
            story_doc = {
                "vision_id": vision_id,
                "category": cat,
                "title": title,
                "desc": desc,
                "photo_file_id": photo_file_id,
                "episodes": [],
                "created_by": message.from_user.id,
                "created_at": time.time()
            }
            stories_col.insert_one(story_doc)

            # Post into DB channel (photo + caption)
            caption = f"Title: {title}\nVision ID: {vision_id}\nCategory: {cat}\n\n{desc}"
            try:
                sent = await client.send_photo(DB_CHANNEL_ID, photo=photo_file_id, caption=caption)
                # save posted message id for reference
                stories_col.update_one({"vision_id": vision_id}, {"$set": {"db_post_msg_id": sent.message_id}}, upsert=False)
            except Exception as e:
                logger.warning(f"Failed to post to DB channel: {e}")

            # clear session
            sessions_col.delete_one({"_id": message.from_user.id})

            # reply and show episode add buttons
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("+AddEP1", callback_data=f"ADMIN_EP|ADD|{vision_id}|Ep1")],
                [InlineKeyboardButton("+AddEP1-10", callback_data=f"ADMIN_EP|ADD|{vision_id}|Ep1-10")],
                [InlineKeyboardButton("+AddEP1-50", callback_data=f"ADMIN_EP|ADD|{vision_id}|Ep1-50")],
                [InlineKeyboardButton("+AddEP1-100", callback_data=f"ADMIN_EP|ADD|{vision_id}|Ep1-100")],
                [InlineKeyboardButton("← Back", callback_data="MENU|MAIN")]
            ])
            await message.reply_text(f"Congrats — story added: {vision_id}", reply_markup=kb)
            return

    # UPDATE flow: expecting vision id or episode link input etc
    if mode == "update":
        if stage == "await_vision":
            vision = message.text.strip()
            st = stories_col.find_one({"vision_id": vision})
            if not st:
                await message.reply_text("Vision ID not found. Check and send again, or type Cancel.")
                return
            # store current vision in session and move to update stage
            sessions_col.update_one({"_id": message.from_user.id}, {"$set": {"vision": vision, "stage": "await_update_choice"}}, upsert=True)
            # show story info and buttons for add episodes after last ep
            last_ep = None
            if st.get("episodes"):
                last_ep = st["episodes"][-1]["ep"]
            else:
                last_ep = None
            # compute next ep start number
            next_num = 1
            if last_ep:
                m = EP_RE.match(last_ep)
                if m:
                    next_num = int(m.group(2) or m.group(1)) + 1
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"+AddEP{next_num}", callback_data=f"ADMIN_EP|UPDATE|{vision}|Ep{next_num}")],
                [InlineKeyboardButton(f"+AddEP{next_num}-{next_num+9}", callback_data=f"ADMIN_EP|UPDATE|{vision}|Ep{next_num}-{next_num+9}")],
                [InlineKeyboardButton("← Back", callback_data="MENU|MAIN")]
            ])
            # send current story info
            try:
                await message.reply_photo(st["photo_file_id"], caption=f"{st['title']}\n\n{st['desc']}", reply_markup=kb)
            except Exception:
                await message.reply_text(f"{st['title']}\n\n{st['desc']}", reply_markup=kb)
            return

    # If sessions exist but text doesn't match expected, ignore or instruct
    await message.reply_text("I didn't understand this step. If you're adding/updating a story, follow the prompts or type Cancel.", reply_markup=back_kb("MENU|MAIN"))

# Photo handler for admin AddNEW
@app.on_message(filters.private & filters.photo)
async def admin_photo(client, message):
    s = sessions_col.find_one({"_id": message.from_user.id})
    if not s:
        return
    if s.get("mode") == "addnew" and s.get("stage") == "await_photo":
        # get highest-quality photo file_id
        file_id = message.photo[-1].file_id
        sessions_col.update_one({"_id": message.from_user.id}, {"$set": {"photo_file_id": file_id, "stage": "await_desc"}}, upsert=True)
        await message.reply_text("Photo saved. Now send story DESCRIPTION (text).", reply_markup=back_kb("MENU|MAIN"))
        return

# ----------------- ADMIN EPISODE CALLBACKS -----------------
@app.on_callback_query(filters.regex(r"^ADMIN_EP\|"))
async def admin_ep_cb(client, cbq):
    # pattern: ADMIN_EP|ADD|vision|Ep1  OR ADMIN_EP|UPDATE|vision|EpX
    parts = cbq.data.split("|")
    if len(parts) != 4:
        await cbq.answer("Bad request")
        return
    _, mode, vision, ep_label = parts
    # mode = ADD or UPDATE
    # set session awaiting link for given vision & ep_label
    sessions_col.update_one({"_id": cbq.from_user.id}, {"$set": {"mode": "ep_add", "vision": vision, "ep_label": ep_label}}, upsert=True)
    await cbq.message.reply_text(f"Send the redirect link(s) for {vision} -> {ep_label}. You can paste shortlink or direct file-share bot link.", reply_markup=back_kb("MENU|MAIN"))

# Admin sends link(s) for episodes (single message)
@app.on_message(filters.private & filters.regex(r"^(https?://|t\.me/|telegram\.me/).+"))
async def admin_episode_link_save(client, message):
    s = sessions_col.find_one({"_id": message.from_user.id})
    if not s or s.get("mode") != "ep_add":
        return
    vision = s.get("vision")
    ep_label = s.get("ep_label")
    link = message.text.strip()
    if not vision or not ep_label:
        await message.reply_text("Session expired or missing data. Start again.", reply_markup=back_kb("MENU|MAIN"))
        sessions_col.delete_one({"_id": message.from_user.id})
        return

    # append episode entry to story
    stories_col.update_one({"vision_id": vision}, {"$push": {"episodes": {"ep": ep_label, "link": link, "type": "manual"}}})
    # clear session
    sessions_col.delete_one({"_id": message.from_user.id})
    # respond and show next possible ep button (simple logic: if ep_label was Ep1 -> show AddEP2)
    m = EP_RE.match(ep_label)
    next_ep_button = None
    if m:
        start = int(m.group(1))
        end = int(m.group(2) or start)
        # next start will be end+1
        next_start = end + 1
        next_ep_button = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"+AddEP{next_start}", callback_data=f"ADMIN_EP|UPDATE|{vision}|Ep{next_start}")],
            [InlineKeyboardButton("← Back", callback_data="MENU|MAIN")]
        ])
    else:
        next_ep_button = back_kb("MENU|MAIN")

    await message.reply_text(f"Link saved for {vision} -> {ep_label}", reply_markup=next_ep_button)

# ----------------- fallback: delete session on /cancel -----------------
@app.on_message(filters.private & filters.command("cancel"))
async def cancel_cmd(client, message):
    sessions_col.delete_one({"_id": message.from_user.id})
    await message.reply_text("Operation cancelled.", reply_markup=main_menu_kb())

# ----------------- STARTUP / SHUTDOWN LOG -----------------
if __name__ == "__main__":
    print("Starting StoryBot...")
    try:
        app.run()
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")


