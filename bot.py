import requests
import os
from dotenv import load_dotenv
from discord_webhook import log_to_discord
from functools import wraps

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
    save_movie