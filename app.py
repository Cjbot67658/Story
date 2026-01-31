from flask import Flask, redirect
import os
from bot.models import # if you implement shortlink redirect here

app = Flask(__name__)

@app.route("/")
def health():
    return "OK", 200

# Optional: shortlink redirect (if you implement shortlinks)
# @app.route("/r/<short>")
# def redirect_short(short):
#     target = lookup in db
#     return redirect(target, code=302)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
