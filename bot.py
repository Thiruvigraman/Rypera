import requests
import os
from dotenv import load_dotenv
from discord_webhook import log_to_discord
from functools import wraps
from db import save_movie, load_movies, delete_movie, rename_movie  # Import necessary functions from db

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment. ⚠️")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

ADMIN_ID = os.getenv('ADMIN_ID')

def is_admin(user_id: int) -> bool:
    """
    Check if a user is an admin.
    
    Args:
    user_id (int): The user ID to check.
    
    Returns:
    bool: True if the user is an admin, False otherwise.
    """
    return str(user_id) == ADMIN_ID

def admin_only(func):
    """
    Decorator to ensure admin access.
    
    Args:
    func: The function to decorate.
    
    Returns:
    function: The decorated function.
    """
    @wraps(func)
    def wrapper(update, context, *args, **kwargs):
        if not is_admin(update.message.from_user.id):
            send_message(update.message.chat_id, "🔒 You are not authorized to use this command. 🚫")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

def send_message(chat_id: str, text: str) -> requests.Response:
    """
    Send a message to a chat.
    
    Args:
    chat_id (str): The chat ID.
    text (str): The message text.
    
    Returns:
    requests.Response: The response from the Telegram API.
    """
    url = f"{BASE_URL}/sendMessage"
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"✅ Message sent to {chat_id}: {text}")
    except Exception as e:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"❌ Failed to send message to {chat_id}: {e} 🔴")
        print(f"❌ Failed to send message: {e}")
    return response

@admin_only
def forward_movie(update, context):
    """
    Handle forwarded movie files.
    
    Args:
    update: The update object.
    context: The context object.
    """
    if update.message.document:
        file_id = update.message.document.file_id
        send_message(update.message.chat_id, "🎬 File received! What is the name of the movie?")
        context.user_data['file_id'] = file_id
    else:
        send_message(update.message.chat_id, "⚠️ Please forward a movie file. 📥")

@admin_only
def save_movie_name(update, context):
    """
    Save the movie name.
    
    Args:
    update: The update object.
    context: The context object.
    """
    if 'file_id' not in context.user_data:
        send_message(update.message.chat_id, "⚠️ No file to associate with a movie name. Please forward the file first. 📥")
        return
    movie_name = update.message.text
    file_id = context.user_data['file_id']
    
    # Save the movie details to the database
    save_movie(file_id, movie_name)
    send_message(update.message.chat_id, f"🎥 Movie '{movie_name}' has been saved successfully! 🎉")

@admin_only
def get_movie_link(update, context):
    """
    Get the movie link by name.
    
    Args:
    update: The update object.
    context: The context object.
    """
    movie_name = update.message.text.split(' ', 1)[1] if len(update.message.text.split(' ', 1)) > 1 else None
    if movie_name:
        movie = load_movies(movie_name)
        if movie:
            send_message(update.message.chat_id, f"🎬 Movie found: {movie_name}\nLink: {movie['link']}")
        else:
            send_message(update.message.chat_id, f"⚠️ Movie '{movie_name}' not found.")
    else:
        send_message(update.message.chat_id, "⚠️ Please provide a movie name.")

@admin_only
def delete_movie_command(update, context):
    """
    Delete a movie from the database.
    
    Args:
    update: The update object.
    context: The context object.
    """
    movie_name = update.message.text.split(' ', 1)[1] if len(update.message.text.split(' ', 1)) > 1 else None
    if movie_name:
        result = delete_movie(movie_name)
        if result:
            send_message(update.message.chat_id, f"🗑️ Movie '{movie_name}' has been deleted.")
        else:
            send_message(update.message.chat_id, f"⚠️ Movie '{movie_name}' not found.")
    else:
        send_message(update.message.chat_id, "⚠️ Please provide a movie name to delete.")

@admin_only
def rename_movie_command(update, context):
    """
    Rename a movie in the database.
    
    Args:
    update: The update object.
    context: The context object.
    """
    movie_name = update.message.text.split(' ', 1)[1] if len(update.message.text.split(' ', 1)) > 1 else None
    if movie_name:
        new_name = context.args[0] if len(context.args) > 0 else None
        if new_name:
            result = rename_movie(movie_name, new_name)
            if result:
                send_message(update.message.chat_id, f"✏️ Movie '{movie_name}' renamed to '{new_name}'.")
            else:
                send_message(update.message.chat_id, f"⚠️ Movie '{movie_name}' not found.")
        else:
            send_message(update.message.chat_id, "⚠️ Please provide a new name for the movie.")
    else:
        send_message(update.message.chat_id, "⚠️ Please provide the movie name to rename.")