import os
import json
import requests
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200  # Response for the root URL

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
BOT_USERNAME = os.getenv('BOT_USERNAME')  # Needed for generating links
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')

if not BOT_TOKEN or not ADMIN_ID or not BOT_USERNAME:
    raise ValueError("Error: Missing BOT_TOKEN, ADMIN_ID, or BOT_USERNAME in environment variables.")

ADMIN_ID = int(ADMIN_ID)
STORAGE_FILE = 'storage.json'
TEMP_FILE_IDS = {}

# Function to log errors to Discord (if webhook is set)
def log_to_discord(message):
    if DISCORD_WEBHOOK:
        requests.post(DISCORD_WEBHOOK, json={"content": message})

# Load stored movies from JSON
def load_movies():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

# Save movies to JSON
def save_movies(movies):
    with open(STORAGE_FILE, 'w') as f:
        json.dump(movies, f, indent=4)

# Send a message to a chat
def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=payload)

# Send a file stored in Telegram using file_id
def send_file(chat_id, file_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    payload = {'chat_id': chat_id, 'document': file_id}
    response = requests.post(url, json=payload)
    message_data = response.json()

    if message_data.get('ok'):
        message_id = message_data['result']['message_id']
        threading.Timer(1800, delete_message, args=[chat_id, message_id]).start()
        send_message(chat_id, "This file will be automatically deleted after 30 minutes.")

# Delete a message
def delete_message(chat_id, message_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'
    payload = {'chat_id': chat_id, 'message_id': message_id}
    requests.post(url, json=payload)

# Process incoming Telegram messages
def process_update(update):
    if 'message' not in update:
        return

    chat_id = update['message']['chat']['id']
    user_id = update['message']['from']['id']
    text = update['message'].get('text', '')
    document = update['message'].get('document')
    video = update['message'].get('video')

    # Handle forwarded files from admin
    if (document or video) and user_id == ADMIN_ID:
        file_id = document['file_id'] if document else video['file_id']
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
        return

    # Store the forwarded file with a name
    if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
        movies = load_movies()
        movies[text] = {"file_id": TEMP_FILE_IDS[chat_id]}
        save_movies(movies)
        send_message(chat_id, f"Movie '{text}' has been added.")
        del TEMP_FILE_IDS[chat_id]
        return

    # Handle /list_files command (Admin Only)
    if text == '/list_files' and user_id == ADMIN_ID:
        movies = load_movies()
        send_message(chat_id, "Stored Files:\n" + "\n".join(movies.keys()) if movies else "No files stored.")
        return

    # Handle /rename_file command (Admin Only)
    if text.startswith('/rename_file') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Usage: /rename_file OldName NewName")
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

    # Handle /delete_file command (Admin Only)
    if text.startswith('/delete_file') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /delete_file FileName")
        else:
            file_name = parts[1]
            movies = load_movies()
            if file_name in movies:
                del movies[file_name]
                save_movies(movies)
                send_message(chat_id, f"Deleted '{file_name}'.")
            else:
                send_message(chat_id, f"Movie '{file_name}' not found.")
        return

    # Handle /get_movie_link command (Admin Only)
    if text.startswith('/get_movie_link') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /get_movie_link Movie Name")
            return
        movie_name = parts[1]
        movies = load_movies()
        if movie_name in movies:
            movie_link = f"https://t.me/{BOT_USERNAME}?start={movie_name.replace(' ', '_')}"
            send_message(chat_id, f"Click here to get the movie: {movie_link}\nThis file will be automatically deleted after 30 minutes.")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found in storage.")
        return

    # Handle /start command when user clicks the generated link
    if text.startswith('/start '):
        movie_name = text.replace('/start ', '').replace('_', ' ')
        movies = load_movies()
        if movie_name in movies and 'file_id' in movies[movie_name]:
            send_file(chat_id, movies[movie_name]['file_id'])
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
        return

# Flask webhook endpoint
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    try:
        update = request.get_json()
        process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)