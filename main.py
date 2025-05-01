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
import signal

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

# Handle clean exit and signals
def on_exit():
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"⚠️ Bot is shutting down. Reason: Process terminated (PID: {os.getpid()})")
    close_db()

atexit.register(on_exit)

# Handle SIGTERM and SIGINT for graceful shutdown
def handle_signal(signum, frame):
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"⚠️ Bot received signal {signum}. Shutting down.")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# Telegram Webhook Route
@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    return handle_webhook()

# Health Check Endpoint
@app.route("/", methods=["GET"])
def home():
    try:
        # Verify MongoDB connection is alive
        client = connect_db.client  # Access the client from database.py
        client.server_info()  # Ping MongoDB
        return "Bot is running!", 200
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[health_check] Failed: {str(e)}")
        return "Bot is unhealthy", 500

# Run Flask app
if __name__ == '__main__':
    import config  # Avoid circular import during logging
    port = int(os.getenv('PORT', 8080))  # Use PORT env var or default to 8080
    app.run(host='0.0.0.0', port=port)