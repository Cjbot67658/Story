# web_and_bot.py (example)
from flask import Flask
from threading import Thread
ffrom bot import start_bot as run_bot # assume bot.py defines a run_bot() or similar entrypoint
import os

app = Flask(__name__)

@app.route("/")
def health():
    return "OK", 200

def run_web():
    # Listen on all interfaces on the configured port
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    # Start Flask in a daemon thread, then start the bot
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()
    run_bot()
