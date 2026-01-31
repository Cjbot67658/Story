# web_and_bot.py
import os
from threading import Thread
from flask import Flask
from bot import run_bot   # IMPORT THE CORRECT NAME (run_bot)

app = Flask(__name__)

@app.route("/")
def health():
    return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    t = Thread(target=run_web, daemon=True)
    t.start()
    run_bot()
