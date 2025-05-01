# main.py

from flask import Flask
from config import BOT_TOKEN
from webhook_handler import handle_webhook
from database import connect_db, close_db
from utils import log_to_discord
import atexit

app = Flask(__name__)

# MongoDB Setup
connect_db()

# On startup
log_to_discord(config.DISCORD_WEBHOOK_STATUS, "Bot is now online!")

# On exit
@atexit.register
def on_exit():
    log_to_discord(config.DISCORD_WEBHOOK_STATUS, "Bot is now offline.")
    close_db()

# Webhook Endpoint
@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    return handle_webhook()

# Home Route
@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

# Run
if __name__ == '__main__':
    import config  # Import config here to avoid circular dependency during startup logging
    app.run(host='0.0.0.0', port=8080)