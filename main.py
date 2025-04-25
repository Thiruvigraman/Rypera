import os
import logging
import atexit
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import CommandHandler, Dispatcher
from dotenv import load_dotenv
from db import load_movies, save_movie, delete_movie, rename_movie
from discord_webhook import log_to_discord

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
def start(update, context):
    update.message.reply_text("👋 Welcome! This is a file share bot.")

def help(update, context):
    if not is_admin(update.message.from_user.id):
        update.message.reply_text("❌ You are not authorized to use this command.")
        return

    update.message.reply_text("""
    ℹ️ Available Commands:
    /add_movie - Add a new movie.
    /delete_movie - Delete a movie.
    /rename_movie - Rename a movie.
    /get_movie_link - Get a movie link.
    """)

# Add handlers to the dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help))

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