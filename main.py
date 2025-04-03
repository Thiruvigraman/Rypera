import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

if not BOT_TOKEN:
    raise ValueError("Error: BOT_TOKEN is missing from environment variables.")
if not ADMIN_ID:
    raise ValueError("Error: ADMIN_ID is missing from environment variables.")
ADMIN_ID = int(ADMIN_ID)

# File to store movie data
STORAGE_FILE = 'storage.json'

# Load existing movie data
def load_movies():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}  # Return empty dictionary if file is corrupted
    return {}

# Save movie data
def save_movies(movies):
    with open(STORAGE_FILE, 'w') as f:
        json.dump(movies, f, indent=4)

# Default route
@app.route('/')
def index():
    return "Bot is running!"

# Webhook handler
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()

    if 'message' not in update:
        return jsonify({"error": "No message found"}), 400

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id']

    # If the message is forwarded
    if 'forward_from' in message or 'forward_from_chat' in message:
        if user_id == ADMIN_ID:
            file_info = None
            movie_name = f"Movie_{len(load_movies()) + 1}"

            # Check for document, video, or audio
            if 'document' in message:
                file_info = message['document']['file_id']
            elif 'video' in message:
                file_info = message['video']['file_id']
            elif 'audio' in message:
                file_info = message['audio']['file_id']

            if file_info:
                movies = load_movies()
                movies[movie_name] = file_info
                save_movies(movies)
                send_message(chat_id, f"Movie '{movie_name}' saved with File ID.")
            else:
                send_message(chat_id, "No valid file found in the forwarded message.")

    # Process commands
    elif 'text' in message:
        command = message['text'].split()

        if command[0] == '/start':
            send_message(chat_id, "Welcome to the Movie Bot! Send me a movie file by forwarding it.")

        elif user_id == ADMIN_ID:
            if command[0] == '/list_movies':
                movies = load_movies()
                if movies:
                    movie_list = "\n".join(f"{name}: {link}" for name, link in movies.items())
                    send_message(chat_id, f"Stored Movies:\n{movie_list}")
                else:
                    send_message(chat_id, "No movies stored.")

            elif command[0] == '/get_movie_link' and len(command) == 2:
                movie_name = command[1]
                movies = load_movies()
                if movie_name in movies:
                    send_message(chat_id, f"File ID for '{movie_name}': `{movies[movie_name]}`")
                else:
                    send_message(chat_id, f"Movie '{movie_name}' not found.")

            elif command[0] == '/delete_movie' and len(command) == 2:
                movie_name = command[1]
                movies = load_movies()
                if movie_name in movies:
                    del movies[movie_name]
                    save_movies(movies)
                    send_message(chat_id, f"Movie '{movie_name}' deleted.")
                else:
                    send_message(chat_id, f"Movie '{movie_name}' not found.")

    return jsonify(success=True)

# Function to send messages to Telegram
def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.post(url, json=payload)

# Set webhook
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f'https://rypera.onrender.com/{BOT_TOKEN}'
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}'
    response = requests.get(url)
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)