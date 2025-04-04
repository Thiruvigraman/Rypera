import os
import json
import requests
import threading
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')

if not BOT_TOKEN:
    raise ValueError("Error: BOT_TOKEN is missing from environment variables.")
if not ADMIN_ID:
    raise ValueError("Error: ADMIN_ID is missing from environment variables.")

ADMIN_ID = int(ADMIN_ID)

# File to store movie data
STORAGE_FILE = 'storage.json'
TEMP_FILE_IDS = {}  # Temporary storage for incoming file IDs

def log_to_discord(message):
    """Logs messages to Discord webhook (if available)."""
    if DISCORD_WEBHOOK:
        requests.post(DISCORD_WEBHOOK, json={"content": message})

def load_movies():
    """Loads stored movies from the JSON file."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            log_to_discord("Warning: storage.json is corrupted, resetting file.")
            return {}
    return {}

def save_movies(movies):
    """Saves movies to the JSON file."""
    with open(STORAGE_FILE, 'w') as f:
        json.dump(movies, f, indent=4)

def send_message(chat_id, text):
    """Sends a text message to a chat."""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=payload)

def send_file(chat_id, file_id):
    """Sends a stored Telegram file using its file_id."""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    payload = {'chat_id': chat_id, 'document': file_id}
    response = requests.post(url, json=payload)

    try:
        message_data = response.json()
        if message_data.get('ok'):
            message_id = message_data['result']['message_id']
            threading.Timer(1800, delete_message, args=[chat_id, message_id]).start()
        else:
            log_to_discord(f"Failed to send file: {message_data}")
    except json.JSONDecodeError:
        log_to_discord("Error: Telegram API response is not JSON.")

def delete_message(chat_id, message_id):
    """Deletes a message from a chat."""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'
    payload = {'chat_id': chat_id, 'message_id': message_id}
    requests.post(url, json=payload)

def process_update(update):
    """Processes incoming Telegram updates."""
    if 'message' not in update:
        return

    chat_id = update['message']['chat']['id']
    user_id = update['message']['from']['id']
    text = update['message'].get('text', '')
    document = update['message'].get('document')
    video = update['message'].get('video')

    if text.startswith('/edit_movie'):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Usage: /edit_movie OldName NewName")
        else:
            _, old_name, new_name = parts
            movies = load_movies()
            if old_name in movies:
                movies[new_name] = movies.pop(old_name)
                save_movies(movies)
                send_message(chat_id, f"Renamed '{old_name}' to '{new_name}'.")
            else:
                send_message(chat_id, f"Movie '{old_name}' not found.")
        return

    if text and text in load_movies():
        movie_data = load_movies()[text]
        if 'file_id' in movie_data:
            send_file(chat_id, movie_data['file_id'])
        return

    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to use this bot.")
        return

    if document or video:
        file_id = document['file_id'] if document else video['file_id']
        send_message(chat_id, "Send the name you want to assign to this file.")
        TEMP_FILE_IDS[chat_id] = file_id
    elif update['message'].get('reply_to_message'):
        original_message = update['message']['reply_to_message']['text']
        if original_message == "Send the name you want to assign to this file.":
            file_name = text
            file_id = TEMP_FILE_IDS.get(chat_id)
            if not file_id:
                send_message(chat_id, "Error: No file was found for this name. Try again.")
                return
            TEMP_FILE_IDS.pop(chat_id)  # Remove only after confirming file exists

            movies = load_movies()
            movies[file_name] = {"file_id": file_id}
            save_movies(movies)
            send_message(chat_id, f"Stored '{file_name}' as a Telegram file.")

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    """Handles incoming Telegram updates via webhook."""
    if request.method == 'POST':
        try:
            update = request.get_json()
            process_update(update)
            return jsonify(success=True)
        except Exception as e:
            log_to_discord(f"Error: {e}")
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)