import os
import logging
import atexit
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Filters, Dispatcher
from dotenv import load_dotenv
from db import load_movies, save_movie, delete_movie, rename_movie
from discord_webhook import log_to_discord
from telegram import ParseMode

# Load environment variables
load_dotenv()

# Set up logging to Discord
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')

# Set up the bot and Flask app
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(BOT_TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, update_queue=None)

# Log to Discord when bot is online
log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now online!")

# Register exit to log when the bot goes offline
def on_exit():
    log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now offline.")
atexit.register(on_exit)

# Command Handlers
def start(update, context):
    update.message.reply_text("Welcome! Type /help for available commands.")

def help(update, context):
    update.message.reply_text("""
    Available Commands:
    /add_movie - Add a new movie.
    /delete_movie - Delete a movie.
    /rename_movie - Rename a movie.
    /get_movie_link - Get a movie link.
    """)

def add_movie(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if user_id == int(os.getenv('ADMIN_ID')):
        if len(context.args) < 2:
            update.message.reply_text("Usage: /add_movie <movie_name> <file_id>")
            return
        
        movie_name = context.args[0]
        file_id = context.args[1]
        save_movie(movie_name, file_id)
        
        # Log the movie addition
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin added a new movie: {movie_name} with file_id: {file_id}")
        update.message.reply_text(f"Movie '{movie_name}' has been added successfully.")

def delete_movie(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if user_id == int(os.getenv('ADMIN_ID')):
        if len(context.args) < 1:
            update.message.reply_text("Usage: /delete_movie <movie_name>")
            return
        
        movie_name = context.args[0]
        delete_movie(movie_name)
        
        # Log the movie deletion
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin deleted movie: {movie_name}")
        update.message.reply_text(f"Movie '{movie_name}' has been deleted successfully.")

def rename_movie(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if user_id == int(os.getenv('ADMIN_ID')):
        if len(context.args) < 2:
            update.message.reply_text("Usage: /rename_movie <old_name> <new_name>")
            return
        
        old_name = context.args[0]
        new_name = context.args[1]
        
        if rename_movie(old_name, new_name):
            # Log movie renaming
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin renamed movie: {old_name} to {new_name}")
            update.message.reply_text(f"Movie '{old_name}' has been renamed to '{new_name}'.")
        else:
            update.message.reply_text(f"Movie '{old_name}' not found.")

def get_movie_link(update, context):
    movie_name = " ".join(context.args)
    movies = load_movies()
    
    if movie_name in movies:
        file_id = movies[movie_name]['file_id']
        link = f"https://t.me/{bot.username}?start={file_id}"
        
        # Log the link generation
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Generated movie link for: {movie_name}")
        update.message.reply_text(f"Click here to access the movie: {link}")
    else:
        update.message.reply_text(f"Movie '{movie_name}' not found.")

# Add handlers to the dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help))
dispatcher.add_handler(CommandHandler("add_movie", add_movie))
dispatcher.add_handler(CommandHandler("delete_movie", delete_movie))
dispatcher.add_handler(CommandHandler("rename_movie", rename_movie))
dispatcher.add_handler(CommandHandler("get_movie_link", get_movie_link))

# Webhook endpoint to handle requests
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    try:
        update = request.get_json()
        dispatcher.process_update(Update.de_json(update, bot))
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# Set the webhook
bot.set_webhook(url=f"https://{os.getenv('WEBHOOK_URL')}/{BOT_TOKEN}")

if __name__ == "__main__":
    app.run(port=5000)