import os
import json
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "YOUR_TELEGRAM_ID"))

# Initialize Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# Initialize Telegram Bot
application = Application.builder().token(BOT_TOKEN).build()

MOVIE_STORAGE = "storage.json"

def load_movies():
    """Load movie data from storage."""
    if os.path.exists(MOVIE_STORAGE):
        with open(MOVIE_STORAGE, "r") as f:
            return json.load(f)
    return {}

def save_movies(movies):
    """Save movie data to storage."""
    with open(MOVIE_STORAGE, "w") as f:
        json.dump(movies, f, indent=4)

MOVIES = load_movies()

# Admin Check
def is_admin(user_id):
    return user_id == ADMIN_ID

# /start Command (For everyone)
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! This bot manages movie links.")

# /add_movie Command (Admin only)
async def add_movie(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        return await update.message.reply_text("You are not authorized.")

    args = context.args
    if len(args) < 2:
        return await update.message.reply_text("Usage: /add_movie <movie_name> <link>")

    movie_name = " ".join(args[:-1])
    link = args[-1]

    MOVIES[movie_name] = link
    save_movies(MOVIES)
    await update.message.reply_text(f"✅ Movie '{movie_name}' added!")

# /get_movie Command (Admin only)
async def get_movie(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        return await update.message.reply_text("You are not authorized.")

    args = context.args
    if not args:
        return await update.message.reply_text("Usage: /get_movie <movie_name>")

    movie_name = " ".join(args)
    link = MOVIES.get(movie_name)

    if link:
        await update.message.reply_text(f"🎬 {movie_name}: {link}")
    else:
        await update.message.reply_text("❌ Movie not found.")

# /list_movies Command (Admin only)
async def list_movies(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        return await update.message.reply_text("You are not authorized.")

    if not MOVIES:
        await update.message.reply_text("No movies stored yet.")
    else:
        movie_list = "\n".join([f"🎬 {name}" for name in MOVIES.keys()])
        await update.message.reply_text(f"📜 Movie List:\n{movie_list}")

# /delete_movie Command (Admin only)
async def delete_movie(update: Update, context: CallbackContext):
    if not is_admin(update.message.from_user.id):
        return await update.message.reply_text("You are not authorized.")

    args = context.args
    if not args:
        return await update.message.reply_text("Usage: /delete_movie <movie_name>")

    movie_name = " ".join(args)
    if movie_name in MOVIES:
        del MOVIES[movie_name]
        save_movies(MOVIES)
        await update.message.reply_text(f"🗑️ Movie '{movie_name}' deleted!")
    else:
        await update.message.reply_text("❌ Movie not found.")

# Webhook route for Telegram
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """Handle Telegram Webhook Updates."""
    update = Update.de_json(request.get_json(), application.bot)
    application.update_queue.put(update)
    return "OK", 200

# Set Webhook on Startup
@app.route("/set_webhook")
def set_webhook():
    """Set webhook for Telegram Bot."""
    url = f"https://rypera.onrender.com/{BOT_TOKEN}"  # Replace with your actual Render URL
    success = application.bot.setWebhook(url)
    return f"Webhook set: {success}"

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add_movie", add_movie))
application.add_handler(CommandHandler("get_movie", get_movie))
application.add_handler(CommandHandler("list_movies", list_movies))
application.add_handler(CommandHandler("delete_movie", delete_movie))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)