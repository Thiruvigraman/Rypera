import requests
import os
from dotenv import load_dotenv
from discord_webhook import log_to_discord
from functools import wraps

# Load .env variables
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment.")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Get admin ID from environment
ADMIN_ID = os.getenv('ADMIN_ID')

# Check if user is admin
def is_admin(user_id: int) -> bool:
    return str(user_id) == ADMIN_ID

# Decorator to ensure admin access
def admin_only(func):
    @wraps(func)
    def wrapper(update, context, *args, **kwargs):
        if not is_admin(update.message.from_user.id):
            send_message(update.message.chat_id, "❌ You are not authorized to use this command.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

# Log and send messages
def send_message(chat_id: str, text: str) -> requests.Response:
    url = f"{BASE_URL}/sendMessage"
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"✅ Message sent to {chat_id}: {text}")
    except Exception as e:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"❌ Failed to send message to {chat_id}: {e}")
        print(f"❌ Failed to send message: {e}")
    return response

# Handle forward movie and get name
@admin_only
def forward_movie(update, context):
    if update.message.document:
        file_id = update.message.document.file_id
        send_message(update.message.chat_id, "📥 File received! What is the name of the movie?")
        context.user_data['file_id'] = file_id
    else:
        send_message(update.message.chat_id, "⚠️ Please forward a movie file.")

# Save the movie with its name
@admin_only
def save_movie_name(update, context):
    if 'file_id' not in context.user_data:
        send_message(update.message.chat_id, "⚠️ No file to associate with a movie name. Please forward the file first.")
        return

    movie_name = update.message.text
    file_id = context.user_data['file_id']
    save_movie(update.message.from_user.id, movie_name, file_id)
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin added a new movie: {movie_name} with file_id: {file_id}")
    send_message(update.message.chat_id, f"✅ Movie '{movie_name}' has been added successfully with the file.")

# Get the movie link
@admin_only
def get_movie_link(update, context):
    movie_name = " ".join(context.args)
    movies = load_movies()

    if movie_name in movies:
        file_id = movies[movie_name]['file_id']
        link = f"https://t.me/{BOT_TOKEN}?start={file_id}"
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Generated movie link for: {movie_name}")
        send_message(update.message.chat_id, f"🎥 Click here to access the movie: {link}")
    else:
        send_message(update.message.chat_id, f"⚠️ Movie '{movie_name}' not found.")

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
dispatcher.add_handler(MessageHandler(Filters.document.mime_type("video/mp4") | Filters.document.mime_type("video/x-matroska"), forward_movie))
dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex(r'^.+$'), save_movie_name))