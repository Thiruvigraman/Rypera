import atexit
from flask import Flask
import config
from database import connect_db, close_db
from webhook_handler import handle_webhook
from utils import log_to_discord

app = Flask(__name__)

# Connect to DB
connect_db()

# On startup
log_to_discord(config.DISCORD_WEBHOOK_STATUS, "Bot is now online!")

@atexit.register
def on_exit():
    log_to_discord(config.DISCORD_WEBHOOK_STATUS, "Bot is now offline.")
    close_db()

@app.route(f"/webhook/{config.BOT_TOKEN}", methods=["POST"])
def webhook():
    return handle_webhook()

@app.route("/")
def home():
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)