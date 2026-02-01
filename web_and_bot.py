# web_and_bot.py
import os
from threading import Thread
from flask import Flask
from bot import run_bot   # make sure bot.py defines run_bot()

app = Flask(__name__)

@app.route("/")
def health():
    return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", "8080"))
    # disable Flask's reloader in production; keep simple server for health checks
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    # When run directly (python web_and_bot.py) start both web + bot.
    # Web runs in a daemon thread so bot runs in main thread (safer for pyrogram).
    t = Thread(target=run_web, daemon=True)
    t.start()
    # run_bot() should block (start pyrogram client) — this is intended
    run_bot()
