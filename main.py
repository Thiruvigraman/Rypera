import os
import json
import requests
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
if not DISCORD_WEBHOOK:
    raise ValueError("Error: DISCORD_WEBHOOK is missing from environment variables.")

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
            return {}
    return {}

# Save movie data
def save_movies(movies):
    with open(STORAGE_FILE, 'w') as f:
        json.dump(movies, f, indent=4)

# Send logs to Discord
def send_discord_log(content):
    data = {"content": content}
    requests.post(DISCORD_WEBHOOK, json=data)

# Default route
@app.route('/')
def index():
    send_discord_log("✅ Bot is running!")
    return "Bot is running!"

# Webhook handler
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if 'message' not in update:
        send_discord_log("⚠️ Received an update with no message!")
        return jsonify({"error": "No message found"}), 400

    chat_id = update['message']['chat']['id']
    user_id = update['message']['from']['id']

    # Log message to Discord
    send_discord_log(f"📩 New message from {user_id}: {update['message']}")

    if 'text' in update['message']:
        command = update['message']['text'].split()

        if command[0] == '/start':
            send_message(chat_id, "Welcome to the Movie Bot!")

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
                    send_message(chat_id, f"File ID for '{movie_name}': {movies[movie_name]}")
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

    # Handle forwarded files (Admin Only)
    if user_id == ADMIN_ID:
        if 'video' in update['message']:
            file_id = update['message']['video']['file_id']
        elif 'document' in update['message']:
            file_id = update['message']['document']['file_id']
        else:
            file_id = None

        if file_id:
            send_message(chat_id, "What name do you want to add to this file?")
            store_pending_files[user_id] = file_id  # Temporarily store file ID
            send_discord_log(f"🆕 File received from {user_id} - ID: {file_id}")

    # Handle name response for forwarded file
    elif user_id in store_pending_files and 'text' in update['message']:
        movie_name = update['message']['text']
        file_id = store_pending_files.pop(user_id)

        movies = load_movies()
        movies[movie_name] = file_id
        save_movies(movies)

        send_message(chat_id, f"Movie '{movie_name}' stored with ID: {file_id}")
        send_discord_log(f"✅ Movie stored: {movie_name} - ID: {file_id}")

    return jsonify(success=True)

# Function to send messages to Telegram
def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=payload)

# Set webhook
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f'https://rypera.onrender.com/{BOT_TOKEN}'
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}'
    response = requests.get(url)
    return jsonify(response.json())

if __name__ == '__main__':
    store_pending_files = {}  # Dictionary to store file IDs temporarily
    send_discord_log("🚀 Bot is starting...")
    app.run(host='0.0.0.0', port=8080)