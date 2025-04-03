import json
import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Load bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Webhook URL (Replace with your actual Render domain)
WEBHOOK_URL = "https://your-render-app.onrender.com"

# Initialize Flask app
app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Telegram bot
application = Application.builder().token(BOT_TOKEN).build()

# Storage file
STORAGE_FILE = "storage.json"

# Load existing movie data
def load_movies():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    return {}

# Save movie data
def save_movies(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Movie storage
movies = load_movies()

# Start command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hello! Send me a movie file, and I'll save it.")

# Handle movie uploads
async def handle_file(update: Update, context: CallbackContext):
    file = update.message.document or update.message.video
    if not file:
        return
    
    file_id = file.file_id
    file_name = file.file_name if hasattr(file, "file_name") else "Unknown"
    
    movies[file_id] = file_name
    save_movies(movies)

    await update.message.reply_text(f"Saved: {file_name} (ID: {file_id})")

# Get movie link (Admin only)
async def get_link(update: Update, context: CallbackContext):
    if update.effective_user.id != int(os.getenv("ADMIN_ID")):
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /getlink <file_id>")
        return

    file_id = args[0]
    if file_id in movies:
        await update.message.reply_text(f"File: {movies[file_id]}\nLink: https://t.me/{BOT_TOKEN}?start={file_id}")
    else:
        await update.message.reply_text("File ID not found.")

# List all movies (Admin only)
async def list_movies(update: Update, context: CallbackContext):
    if update.effective_user.id != int(os.getenv("ADMIN_ID")):
        return

    if not movies:
        await update.message.reply_text("No movies stored.")
    else:
        movie_list = "\n".join([f"{name} - {fid}" for fid, name in movies.items()])
        await update.message.reply_text(f"Movies:\n{movie_list}")

# Telegram bot handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("getlink", get_link))
application.add_handler(CommandHandler("list", list_movies))
application.add_handler(MessageHandler(filters.Document.ALL | filters.Video, handle_file))

# Flask route for webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    application.process_update(update)
    return "OK", 200

# Set webhook
async def start_bot():
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())

    app.run(host="0.0.0.0", port=5000)  # For local testing