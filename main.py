import os
import logging
import atexit
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import CommandHandler, Dispatcher, MessageHandler, Filters
from dotenv import load_dotenv
from db import load_movies, save_movie, delete_movie, rename_movie
from discord_webhook import log_to_discord
from bot import start, help, forward_movie, save_movie_name, get_movie_link

# Load environment variables
load_dotenv()

# Set up logging to Discord
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')

# Set up the bot and Flask app
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(BOT_TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, update_queue=None)

# Log to Discord when bot is online
log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ Bot is now online!")

# Register exit to log when the bot goes offline
def on_exit():
    log_to_discord(DISCORD_WEBHOOK_STATUS, "❌ Bot is now offline.")
atexit.register(on_exit)

# Admin check function
def is_admin(user_id: int) -> bool:
    return user_id == int(os.getenv('ADMIN_ID'))

# Command Handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help))
dispatcher.add_handler(CommandHandler("get_movie_link", get_movie_link))
dispatcher.add_handler(MessageHandler(Filters.document.mime_type("video/mp4") | Filters.document.mime_type("video/x-matroska"), forward_movie))
dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex(r'^.+$'), save_movie_name))

# Webhook endpoint to handle requests
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    try:
        update = request.get_json()
        dispatcher.process_update(Update.de_json(update, bot))
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

# Set the webhook
bot.set_webhook(url=f"https://{os.getenv('WEBHOOK_URL')}/{BOT_TOKEN}")

if __name__ == "__main__":
    app.run(port=5000)