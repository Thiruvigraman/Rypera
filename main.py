#main.py
from flask import Flask
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS
from webhook_handler import handle_webhook
from database import connect_db, close_db
from utils import log_to_discord
import atexit
import sys
import traceback
import os

app = Flask(__name__)

# Connect to MongoDB at startup
try:
    connect_db()
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🚀 Bot is now online.")
except Exception as e:
    error_message = f"❌ Startup failed: {str(e)}\n{traceback.format_exc()}"
    log_to_discord(DISCORD_WEBHOOK_STATUS, error_message)
    print(error_message)
    sys.exit(1)  # Exit if database connection fails

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
    port = int(os.getenv('PORT', 8080))  # Use PORT env var or default to 8080
    app.run(host='0.0.0.0', port=port)