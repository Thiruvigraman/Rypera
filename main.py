#main.py

import os
import requests
import threading
import atexit
from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask app setup
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

# Environment Variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
BOT_USERNAME = os.getenv('BOT_USERNAME')
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')
MONGODB_URI = os.getenv('MONGODB_URI')

if not BOT_TOKEN or not ADMIN_ID or not BOT_USERNAME or not MONGODB_URI:
    raise ValueError("Missing required environment variables")

ADMIN_ID = int(ADMIN_ID)
TEMP_FILE_IDS = {}

# Webhook logger
def log_to_discord(webhook, message):
    if webhook:
        try:
            requests.post(webhook, json={"content": message})
        except Exception:
            pass

# MongoDB setup
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client['telegram_bot']
    movies_collection = db['movies']
    log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.")
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ MongoDB connection failed: {e}")
    raise e

# On startup
log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now online!")

# On exit
def on_exit():
    log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now offline.")
atexit.register(on_exit)

# MongoDB operations
def load_movies():
    return {doc['name']: {"file_id": doc['file_id']} for doc in movies_collection.find()}

def save_movie(name, file_id):
    movies_collection.update_one({"name": name}, {"$set": {"file_id": file_id}}, upsert=True)

def delete_movie(name):
    movies_collection.delete_one({"name": name})

def rename_movie(old_name, new_name):
    movie = movies_collection.find_one({"name": old_name})
    if movie:
        delete_movie(old_name)
        save_movie(new_name, movie['file_id'])
        return True
    return False

# Telegram methods
def send_message(chat_id, text, parse_mode=None):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    return requests.post(url, json=payload).json()

def send_file(chat_id, file_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    payload = {'chat_id': chat_id, 'document': file_id}
    response = requests.post(url, json=payload)
    data = response.json()

    if data.get('ok'):
        file_msg_id = data['result']['message_id']

        warning_text = (
            "❗️ *IMPORTANT* ❗️\n\n"
            "This Video / File Will Be Deleted In *30 minutes* _(Due To Copyright Issues)_\n\n"
            "📌 *Please Forward This Video / File To Somewhere Else And Start Downloading There.*"
        )
        warn_resp = send_message(chat_id, warning_text, parse_mode="Markdown")
        warn_msg_id = warn_resp['result']['message_id']

        threading.Timer(1800, delete_message, args=[chat_id, file_msg_id]).start()
        threading.Timer(1800, delete_message, args=[chat_id, warn_msg_id]).start()

def delete_message(chat_id, message_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'
    payload = {'chat_id': chat_id, 'message_id': message_id}
    requests.post(url, json=payload)

# Handle updates
def process_update(update):
    if 'message' not in update:
        return

    chat_id = update['message']['chat']['id']
    user_id = update['message']['from']['id']
    text = update['message'].get('text', '')
    document = update['message'].get('document')
    video = update['message'].get('video')

    # Admin uploading a file
    if (document or video) and user_id == ADMIN_ID:
        file_id = document['file_id'] if document else video['file_id']
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
        return

    # Admin saving a file
    if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
        save_movie(text, TEMP_FILE_IDS[chat_id])
        send_message(chat_id, f"Movie '{text}' has been added.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie added: {text}")
        del TEMP_FILE_IDS[chat_id]
        return

    # List movies
    if text == '/list_files' and user_id == ADMIN_ID:
        movies = load_movies()
        msg = "Stored Files:\n" + "\n".join(movies.keys()) if movies else "No files stored."
        send_message(chat_id, msg)
        return

    # Rename
    if text.startswith('/rename_file') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Usage: /rename_file OldName NewName")
        else:
            _, old, new = parts
            if rename_movie(old, new):
                send_message(chat_id, f"Renamed '{old}' to '{new}'.")
                log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Renamed '{old}' to '{new}'")
            else:
                send_message(chat_id, f"Movie '{old}' not found.")
        return

    # Delete
    if text.startswith('/delete_file') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /delete_file FileName")
        else:
            name = parts[1]
            delete_movie(name)
            send_message(chat_id, f"Deleted '{name}'.")
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Deleted movie: {name}")
        return

    # Generate link
    if text.startswith('/get_movie_link') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /get_movie_link Movie Name")
            return
        name = parts[1]
        movies = load_movies()
        if name in movies:
            safe_name = name.replace(" ", "_")
            link = f"https://t.me/{BOT_USERNAME}?start={safe_name}"
            send_message(chat_id, f"Click here to get the movie: {link}")
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Generated link for: {name}")
        else:
            send_message(chat_id, f"Movie '{name}' not found.")
        return

    # User access
    if text.startswith('/start '):
        name = text.replace('/start ', '').replace('_', ' ')
        movies = load_movies()
        if name in movies:
            send_file(chat_id, movies[name]['file_id'])
            log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"{user_id} accessed movie: {name}")
        else:
            send_message(chat_id, f"Movie '{name}' not found.")
        return

# Webhook endpoint
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# Run app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)