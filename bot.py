import os
import requests
from dotenv import load_dotenv
from db import add_movie, get_movie, update_movie, delete_movie
from discord_webhook import log_movie_action, log_error

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv("ADMIN_ID"))

def handle_telegram_update(request):
    if request.method == 'POST':
        json_data = request.get_json()
        message = json_data.get('message')
        if not message:
            return 'No message found', 400

        chat_id = message['chat']['id']
        command = message.get('text', '')

        if command == '/start':
            send_message(chat_id, "Welcome to the Movie Bot!")

        elif chat_id == ADMIN_ID:
            if command == '/add_movie':
                movie_data = {"title": "Movie Title", "description": "Movie Description"}
                if add_movie(movie_data):
                    log_movie_action('added', movie_data['title'], 'N/A')
                    send_message(chat_id, "Movie added successfully.")
                else:
                    send_message(chat_id, "Failed to add movie.")

            elif command == '/get_movie':
                movie = get_movie("Movie Title")
                if movie:
                    send_message(chat_id, f"Movie found: {movie['title']} - {movie['description']}")
                else:
                    send_message(chat_id, "Movie not found.")

            elif command == '/update_movie':
                updated_data = {"description": "Updated Movie Description"}
                if update_movie("Movie Title", updated_data):
                    log_movie_action('renamed', "Movie Title", 'N/A')
                    send_message(chat_id, "Movie updated successfully.")
                else:
                    send_message(chat_id, "Failed to update movie.")

            elif command == '/delete_movie':
                if delete_movie("Movie Title"):
                    log_movie_action('deleted', "Movie Title", 'N/A')
                    send_message(chat_id, "Movie deleted successfully.")
                else:
                    send_message(chat_id, "Failed to delete movie.")
            else:
                send_message(chat_id, "Unknown command.")
        else:
            send_message(chat_id, "You are not authorized to use this command.")

    return 'OK', 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    try:
        response = requests.post(url, data=payload)
        return response.json()
    except Exception as e:
        log_error(f"Failed to send message: {e}")
        return None