import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Load or create storage file
STORAGE_FILE = "storage.json"
if os.path.exists(STORAGE_FILE):
    with open(STORAGE_FILE, "r") as f:
        movie_data = json.load(f)
else:
    movie_data = {}

# Admin user ID (Replace with your Telegram user ID)
ADMIN_ID = 6778132055  # Change this to your Telegram user ID

# Function to save data
def save_data():
    with open(STORAGE_FILE, "w") as f:
        json.dump(movie_data, f, indent=4)

# Start command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hello! Forward a movie file to me, and I'll store its ID.")

# Handle forwarded movies
async def handle_forwarded(update: Update, context: CallbackContext):
    if update.message.video:
        file_id = update.message.video.file_id
        file_name = update.message.video.file_name or "Unknown"

        movie_data[file_name] = file_id
        save_data()
        await update.message.reply_text(f"✅ Stored: {file_name}\nID: `{file_id}`")

# Get movie link (Admin only)
async def get_link(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/getlink movie_name`")
        return
    
    movie_name = " ".join(args)
    file_id = movie_data.get(movie_name)

    if file_id:
        await update.message.reply_text(f"🎬 Movie: {movie_name}\n🆔 ID: `{file_id}`")
    else:
        await update.message.reply_text("❌ Movie not found.")

# List all movies (Admin only)
async def list_movies(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return

    if not movie_data:
        await update.message.reply_text("📂 No movies stored.")
    else:
        movie_list = "\n".join(movie_data.keys())
        await update.message.reply_text(f"🎥 Stored Movies:\n{movie_list}")

# Edit movie ID (Admin only)
async def edit_movie(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/edit movie_name new_id`")
        return

    movie_name = " ".join(args[:-1])
    new_id = args[-1]

    if movie_name in movie_data:
        movie_data[movie_name] = new_id
        save_data()
        await update.message.reply_text(f"✅ Updated: {movie_name}\nNew ID: `{new_id}`")
    else:
        await update.message.reply_text("❌ Movie not found.")

# Delete movie (Admin only)
async def delete_movie(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/delete movie_name`")
        return

    movie_name = " ".join(args)
    if movie_name in movie_data:
        del movie_data[movie_name]
        save_data()
        await update.message.reply_text(f"🗑 Deleted: {movie_name}")
    else:
        await update.message.reply_text("❌ Movie not found.")

# Create bot application
application = Application.builder().token("YOUR_BOT_TOKEN").build()

# Command Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("getlink", get_link))
application.add_handler(CommandHandler("listmovies", list_movies))
application.add_handler(CommandHandler("edit", edit_movie))
application.add_handler(CommandHandler("delete", delete_movie))

# Handle forwarded video files
application.add_handler(MessageHandler(filters.VIDEO & filters.FORWARDED, handle_forwarded))

# Start bot
application.run_polling()