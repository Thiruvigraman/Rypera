import os
import sys
import signal
import logging
from flask import Flask, request
from dotenv import load_dotenv
from commands import process_update, connect_mongo, create_embed
from discord_webhook import log_to_discord

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
BOT_TOKEN = os.getenv('BOT_TOKEN')
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')

# Flask app
app = Flask(__name__)

# MongoDB setup
connect_mongo()

# Root route for health check
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200

# Webhook endpoint
@app.route('/webhook/<token>', methods=['POST'])
def webhook(token):
    if token != BOT_TOKEN:
        return "Unauthorized", 403
    update = request.get_json()
    process_update(update)
    return "OK", 200

# Graceful shutdown
def shutdown_handler(signal_num, frame):
    embed = create_embed(
        title="🔴 Bot Offline",
        description="The bot has gone offline.",
        color=0xe74c3c
    )
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🔴 Bot went offline!", embed)
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# Start the app
if __name__ == '__main__':
    embed = create_embed(
        title="🟢 Bot Online",
        description="The bot is online and ready to use!",
        color=0x2ecc71
    )
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🟢 Bot is Online and Running!", embed)
    app.run(host="0.0.0.0", port=5000)