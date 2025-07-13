# main.py
import atexit
import os
from flask import Flask, request, jsonify
from handlers import process_update
from discord import log_to_discord
from config import DISCORD_WEBHOOK_STATUS, BOT_TOKEN

app = Flask(__name__)

# Flag to track intentional shutdown
is_shutting_down = False

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
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error in webhook: {e}")
        return jsonify({"error": str(e)}), 500

# On startup
log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now online!")

# On exit
def on_exit():
    if is_shutting_down:
        log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now offline (intentional shutdown).")
    else:
        log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot process terminated unexpectedly.")

# Register the exit handler
atexit.register(on_exit)

# Optional: Add a shutdown endpoint for intentional shutdown (for admin use)
@app.route('/shutdown', methods=['POST'])
def shutdown():
    global is_shutting_down
    if request.json.get('admin_id') == str(ADMIN_ID):  # Ensure only admin can trigger
        is_shutting_down = True
        log_to_discord(DISCORD_WEBHOOK_STATUS, "Shutdown initiated by admin.")
        # Gracefully terminate the process
        os._exit(0)
        return jsonify({"status": "Shutting down"})
    return jsonify({"error": "Unauthorized"}), 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)