import json
import logging
import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Telegram Bot Token
BOT_TOKEN = "YOUR_BOT_TOKEN"

# Your Telegram user ID (Admin Only)
ADMIN_ID = YOUR_ADMIN_TELEGRAM_ID  

# Storage file
STORAGE_FILE = "storage.json"

# Initialize Flask app for webhook
app = Flask(__name__)

# Enable logging
logging.basicConfig(level=logging.INFO)

# Load or create storage file
if os.path.exists(STORAGE_FILE):
    with open(STORAGE_FILE, "r") as f:
        movies = json.load(f)
else:
    movies = {}

def save_storage(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f)

# Admin-only check
def admin_only(func):
    async def wrapper(update: Update, context: CallbackContext):
        if update.message.from_user.id != ADMIN_ID:
            return await update.message.reply_text("❌ You are not authorized to use this command.")
        return await func(update, context)
    return wrapper

# Start Command (Everyone)
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("🤖 Welcome! Use this bot to manage movie links.")

# Handle Movie Uploads (Video & Document)
async def handle_file(update: Update, context: CallbackContext):
    message = update.message
    file = message.video or message.document
    if file:
        file_id = file.file_id
        file_name = file.file_name or "Unknown"
        movies[file_name] = file_id
        save_storage(movies)
        await message.reply_text(f"✅ Movie '{file_name}' stored!")

# List Movies (Admin Only)
@admin_only
async def list_movies(update: Update, context: CallbackContext):
    if not movies:
        return await update.message.reply_text("No movies stored yet.")
    movie_list = "\n".join(movies.keys())
    await update.message.reply_text(f"🎬 Stored Movies:\n{movie_list}")

# Delete a Movie (Admin Only)
@admin_only
async def delete_movie(update: Update, context: CallbackContext):
    if not context.args:
        return await update.message.reply_text("Usage: /delete_movie <movie_name>")
    movie_name = " ".join(context.args)
    if movie_name in movies:
        del movies[movie_name]
        save_storage(movies)
        await update.message.reply_text(f"✅ Movie '{movie_name}' deleted successfully!")
    else:
        await update.message.reply_text("❌ Movie not found.")

# Get Movie Link (Admin Only)
@admin_only
async def get_movie_link(update: Update, context: CallbackContext):
    if not context.args:
        return await update.message.reply_text("Usage: /get_movie_link <movie_name>")
    movie_name = " ".join(context.args)
    file_id = movies.get(movie_name)
    if file_id:
        await update.message.reply_text(f"🎥 Movie Link:\n`{file_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Movie not found.")

# Telegram Webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    application.update_queue.put(update)
    return "OK", 200

# Initialize Telegram Bot
application = Application.builder().token(BOT_TOKEN).build()

# Register Handlers
application.add_handler(CommandHandler("start", start))  # Open for everyone
application.add_handler(CommandHandler("list_movies", list_movies))
application.add_handler(CommandHandler("delete_movie", delete_movie))
application.add_handler(CommandHandler("get_movie_link", get_movie_link))
application.add_handler(MessageHandler(filters.Document.ALL | filters.Video, handle_file))

# Start Flask Webhook
if __name__ == "__main__":
    app.run(port=5000)