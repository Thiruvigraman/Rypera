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

# Command Handlers
@admin_only
def add_movie(update, context):
    if len(context.args) < 2:
        send_message(update.message.chat_id, "⚠️ Usage: /add_movie <movie_name> <file_id>")
        return

    movie_name = context.args[0]
    file_id = context.args[1]
    save_movie(update.message.from_user.id, movie_name, file_id)
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin added a new movie: {movie_name} with file_id: {file_id}")
    send_message(update.message.chat_id, f"✅ Movie '{movie_name}' has been added successfully.")

@admin_only
def delete_movie(update, context):
    if len(context.args) < 1:
        send_message(update.message.chat_id, "⚠️ Usage: /delete_movie <movie_name>")
        return

    movie_name = context.args[0]
    delete_movie(update.message.from_user.id, movie_name)
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin deleted movie: {movie_name}")
    send_message(update.message.chat_id, f"✅ Movie '{movie_name}' has been deleted successfully.")

@admin_only
def rename_movie(update, context):
    if len(context.args) < 2:
        send_message(update.message.chat_id, "⚠️ Usage: /rename_movie <old_name> <new_name>")
        return

    old_name = context.args[0]
    new_name = context.args[1]

    if rename_movie(update.message.from_user.id, old_name, new_name):
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin renamed movie: {old_name} to {new_name}")
        send_message(update.message.chat_id, f"✅ Movie '{old_name}' has been renamed to '{new_name}'.")
    else:
        send_message(update.message.chat_id, f"⚠️ Movie '{old_name}' not found.")

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