# main.py
from flask import Flask
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS
from webhook_handler import handle_webhook
from database import connect_db, close_db
from utils import log_to_discord
import atexit

app = Flask(__name__)

# Connect to MongoDB at startup
try:
    connect_db()
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🚀 Bot is now online.")
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ Startup failed: {e}")

# Handle clean exit
@atexit.register
def on_exit():
    log_to_discord(DISCORD_WEBHOOK_STATUS, "⚠️ Bot is shutting down.")
    close_db()

# Telegram Webhook Route
@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    return handle_webhook()

# Health Check Endpoint
@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

# Run Flask app
if __name__ == '__main__':
    import config  # Avoid circular import during logging
    app.run(host='0.0.0.0', port=8080)