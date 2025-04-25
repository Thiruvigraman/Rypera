import requests
import os
from dotenv import load_dotenv
from discord_webhook import log_to_discord

# Load .env variables
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment.")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Get admin ID from environment
ADMIN_ID = os.getenv('ADMIN_ID')

# Check if user is admin
def is_admin(user_id):
    return str(user_id) == ADMIN_ID

def send_message(chat_id: str, text: str):
    url = f"{BASE_URL}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        # Optionally, log the successful send to Discord
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Message sent to {chat_id}: {text}")
    except Exception as e:
        # Log error to Discord if sending message fails
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Failed to send message to {chat_id}: {e}")
        print(f"Failed to send message: {e}")
    return response

def send_file(chat_id: str, file_id: str):
    url = f"{BASE_URL}/sendDocument"
    data = {
        'chat_id': chat_id,
        'document': file_id
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        # Optionally, log the successful file send to Discord
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"File sent to {chat_id}: {file_id}")
    except Exception as e:
        # Log error to Discord if sending file fails
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Failed to send file to {chat_id}: {e}")
        print(f"Failed to send file: {e}")
    return response

def handle_command(update, context, command, args=None):
    user_id = update.message.from_user.id

    if command == "/start":
        # /start command is available to everyone
        send_message(update.message.chat_id, "Welcome! This is a file share bot.")
        return
    
    if not is_admin(user_id):
        send_message(update.message.chat_id, "You are not authorized to use this command.")
        return

    if command == "/add_movie":
        if len(args) < 2:
            send_message(update.message.chat_id, "Usage: /add_movie <movie_name> <file_id>")
            return
        movie_name = args[0]
        file_id = args[1]
        # Implement save_movie function to save the movie
        # save_movie(movie_name, file_id)
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Admin added a new movie: {movie_name} with file_id: {file_id}")
        send_message(update.message.chat_id, f"Movie '{movie_name}' has been added successfully.")

    elif command == "/delete_movie":
        if len(args) < 1:
            send_message(update.message.chat_id, "Usage: /delete_movie <movie_name>")
            return
        movie_name = args[0]
        # Implement delete_movie function to delete the movie
        # delete_movie(movie_name)
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Admin deleted movie: {movie_name}")
        send_message(update.message.chat_id, f"Movie '{movie_name}' has been deleted successfully.")

    elif command == "/rename_movie":
        if len(args) < 2:
            send_message(update.message.chat_id, "Usage: /rename_movie <old_name> <new_name>")
            return
        old_name = args[0]
        new_name = args[1]
        # Implement rename_movie function to rename the movie
        # rename_movie(old_name, new_name)
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Admin renamed movie: {old_name} to {new_name}")
        send_message(update.message.chat_id, f"Movie '{old_name}' has been renamed to '{new_name}'.")

    elif command == "/get_movie_link":
        movie_name = " ".join(args)
        # Implement load_movies to load movie data
        # movies = load_movies()
        movies = {}  # Replace with actual loading of movie data
        if movie_name in movies:
            file_id = movies[movie_name]['file_id']
            link = f"https://t.me/{BOT_TOKEN}?start={file_id}"
            log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Generated movie link for: {movie_name}")
            send_message(update.message.chat_id, f"Click here to access the movie: {link}")
        else:
            send_message(update.message.chat_id, f"Movie '{movie_name}' not found.")

# Example of how to call the handle_command function when processing a message:
# This is a simplified example; you'd need to integrate this with your actual Telegram bot message handler.
def process_message(update):
    message = update.message.text
    if message.startswith("/"):
        command, *args = message.split()
        handle_command(update, None, command, args)

# Example update from Telegram
# update = Update(...)  # Create or receive the actual update object
# process_message(update)