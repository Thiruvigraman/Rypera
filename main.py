# main.py
import atexit
from flask import Flask, request, jsonify
from handlers import process_update
from discord import log_to_discord
from config import DISCORD_WEBHOOK_STATUS, BOT_TOKEN

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

# Webhook Endpoint
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    try:
        update = request.get_json()
        process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# On startup
log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now online!")

# On exit
def on_exit():
    log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now offline.")
atexit.register(on_exit)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)