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

    chat_id = update['message']['chat']['id']
    user_id = update['message']['from']['id']
    message = update['message']

    # Public Command (Everyone can use /start)
    if 'text' in message and message['text'] == '/start':
        send_message(chat_id, "Welcome to the Movie Bot! Forward any movie file to store it (Admins only).")
        return jsonify(success=True)

    # **Restrict all commands and file storage to Admin only**
    if user_id != ADMIN_ID:
        send_message(chat_id, "Unauthorized access! Only the admin can use this bot.")
        return jsonify(success=False)

    # Handling forwarded media files (movies) (Admin Only)
    if 'document' in message:
        file_id = message['document']['file_id']
        file_name = message['document']['file_name']

    elif 'video' in message:
        file_id = message['video']['file_id']
        file_name = f"video_{file_id}.mp4"  # Use ID as filename if missing

    else:
        file_id = None
        file_name = None

    if file_id and file_name:
        movies = load_movies()
        movies[file_name] = file_id
        save_movies(movies)
        send_message(chat_id, f"✅ Movie '{file_name}' stored with ID: {file_id}")

    # Handling admin commands
    if 'text' in message:
        command = message['text'].split()

        if command[0] == '/list_movies':
            movies = load_movies()
            if movies:
                movie_list = "\n".join(movies.keys())
                send_message(chat_id, f"🎬 **Stored Movies:**\n{movie_list}")
            else:
                send_message(chat_id, "📂 No movies stored.")

        elif command[0] == '/get_movie_link' and len(command) == 2:
            movie_name = command[1]
            movies = load_movies()
            if movie_name in movies:
                send_document(chat_id, movies[movie_name])  # Sends the actual file
            else:
                send_message(chat_id, f"❌ Movie '{movie_name}' not found.")

    return jsonify(success=True)

# Function to send messages
def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.post(url, json=payload)

# Function to send stored movie file
def send_document(chat_id, file_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    payload = {'chat_id': chat_id, 'document': file_id}
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