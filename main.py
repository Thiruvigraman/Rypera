import os
import signal
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from commands import process_update, connect_mongo, create_embed
from discord_webhook import log_to_discord

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Config
BOT_TOKEN = os.getenv('BOT_TOKEN')
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')

if not BOT_TOKEN:
    logger.error("BOT_TOKEN is not set in environment variables.")
    raise ValueError("BOT_TOKEN is missing.")

# Flask app
app = Flask(__name__)

# MongoDB setup
connect_mongo()

@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200

@app.route("/webhook/<token>", methods=["POST"])
def webhook(token):
    if token != BOT_TOKEN:
        logger.warning("Unauthorized access attempt with token: %s", token)
        return jsonify({"error": "Unauthorized"}), 403
    update = request.get_json()
    if not update:
        return jsonify({"error": "No update payload provided"}), 400
    process_update(update)
    return jsonify({"status": "OK"}), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error"}), 500

# Graceful shutdown
def shutdown_handler(signal_num, frame):
    embed = create_embed(
        title="ðŸ”´ Bot Offline",
        description="The bot has stopped running.",
        color=0xFF0000
    )
    log_to_discord(DISCORD_WEBHOOK_STATUS, embed)
    logger.info("Bot shutting down...")
    exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))