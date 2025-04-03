import os
 import json
 import requests
 from flask import Flask, request, jsonify

app = Flask(__name__)

Load environment variables

BOT_TOKEN = os.getenv('BOT_TOKEN') ADMIN_ID = os.getenv('ADMIN_ID') DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')

if not BOT_TOKEN: raise ValueError("Error: BOT_TOKEN is missing from environment variables.") if not ADMIN_ID: raise ValueError("Error: ADMIN_ID is missing from environment variables.") ADMIN_ID = int(ADMIN_ID)

File to store movie data

STORAGE_FILE = 'storage.json'

def log_to_discord(message): if DISCORD_WEBHOOK: requests.post(DISCORD_WEBHOOK, json={"content": message})

def load_movies(): if os.path.exists(STORAGE_FILE): try: with open(STORAGE_FILE, 'r') as f: return json.load(f) except json.JSONDecodeError: return {} return {}

def save_movies(movies): with open(STORAGE_FILE, 'w') as f: json.dump(movies, f, indent=4)

def send_message(chat_id, text): url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage' payload = {'chat_id': chat_id, 'text': text} requests.post(url, json=payload)

def request_movie_name(chat_id, file_id): url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage' payload = { 'chat_id': chat_id, 'text': 'What name do you want to assign to this file?', 'reply_markup': json.dumps({"force_reply": True}) } requests.post(url, json=payload)

def store_movie(file_name, file_id): movies = load_movies() movies[file_name] = file_id save_movies(movies) log_to_discord(f"Stored movie: {file_name} ({file_id})")

def process_update(update): if 'message' not in update: return

chat_id = update['message']['chat']['id']
user_id = update['message']['from']['id']
text = update['message'].get('text', '')
document = update['message'].get('document')
video = update['message'].get('video')

if text == '/start':
    send_message(chat_id, "Welcome to the Movie Bot!")
    return

if user_id != ADMIN_ID:
    send_message(chat_id, "You are not authorized to use this bot.")
    return

if text.startswith('/add_movie'):
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        send_message(chat_id, "Usage: /add_movie MovieName MovieLink")
    else:
        _, movie_name, link = parts
        store_movie(movie_name, link)
        send_message(chat_id, f"Movie '{movie_name}' added.")

elif text.startswith('/delete_movie'):
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /delete_movie MovieName")
    else:
        _, movie_name = parts
        movies = load_movies()
        if movie_name in movies:
            del movies[movie_name]
            save_movies(movies)
            send_message(chat_id, f"Movie '{movie_name}' deleted.")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")

elif text == '/list_movies':
    movies = load_movies()
    movie_list = '\n'.join(f"{name}: {link}" for name, link in movies.items()) or "No movies stored."
    send_message(chat_id, f"Stored Movies:\n{movie_list}")

elif text.startswith('/get_movie_link'):
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /get_movie_link MovieName")
    else:
        movie_name = parts[1]
        movies = load_movies()
        link = movies.get(movie_name)
        if link:
            send_message(chat_id, f"Link for '{movie_name}': {link}")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")

elif document or video:
    file_id = document['file_id'] if document else video['file_id']
    request_movie_name(chat_id, file_id)
    log_to_discord(f"Received file: {file_id} from {user_id}")

elif update['message'].get('reply_to_message') and update['message']['reply_to_message']['text'] == 'What name do you want to assign to this file?':
    file_name = text
    file_id = update['message']['reply_to_message']['message_id']
    store_movie(file_name, file_id)
    send_message(chat_id, f"Stored '{file_name}' with ID {file_id}")

def webhook(): try: update = request.get_json() process_update(update) except Exception as e: log_to_discord(f"Error: {e}") return jsonify({"error": str(e)}), 500 return jsonify(success=True)

@app.route('/') def index(): return "Bot is running!"

@app.route(f'/{BOT_TOKEN}', methods=['POST']) def handle_webhook(): return webhook()

@app.route('/set_webhook', methods=['GET']) def set_webhook(): webhook_url = f'https://yourdomain.com/{BOT_TOKEN}' url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}' response = requests.get(url) return jsonify(response.json())

if name == 'main': app.run(host='0.0.0.0', port=8080)

