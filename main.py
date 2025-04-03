import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# File to store movie data
STORAGE_FILE = 'storage.json'

# Load existing movie data
def load_movies():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save movie data
def save_movies(movies):
    with open(STORAGE_FILE, 'w') as f:
        json.dump(movies, f)

# Default route
@app.route('/')
def index():
    return "Bot is running!"

# Webhook handler
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    chat_id = update['message']['chat']['id']
    user_id = update['message']['from']['id']
    command = update['message']['text'].split()

    if command[0] == '/start':
        send_message(chat_id, "Welcome to the Movie Bot!")

    elif user_id == ADMIN_ID:
        if command[0] == '/add_movie' and len(command) == 3:
            movie_name = command[1]
            link = command[2]
            movies = load_movies()
            movies[movie_name] = link
            save_movies(movies)
            send_message(chat_id, f"Movie '{movie_name}' added.")

        elif command[0] == '/delete_movie' and len(command) == 2:
            movie_name = command[1]
            movies = load_movies()
            if movie_name in movies:
                del movies[movie_name]
                save_movies(movies)
                send_message(chat_id, f"Movie '{movie_name}' deleted.")
            else:
                send_message(chat_id, f"Movie '{movie_name}' not found.")

        elif command[0] == '/list_movies':
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
                send_message(chat_id, f"Link for '{movie_name}': {movies[movie_name]}")
            else:
                send_message(chat_id, f"Movie '{movie_name}' not found.")

    return jsonify(success=True)

# Function to send messages to Telegram
def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=payload)

# Set webhook
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url=https://<your_render_app>.render.com/{BOT_TOKEN}'
    response = requests.get(url)
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)