import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Environment Variables
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
MONGO_URI = os.getenv('MONGO_URI')
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')
BOT_USERNAME = os.getenv('BOT_USERNAME')
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client['movie_bot']
movies_collection = db['movies']

# Flask app
app = Flask(__name__)

# Temporary storage for uploaded files
TEMP_FILE_IDS = {}

# Helper functions
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    requests.post(url, json=payload)

def send_file(chat_id, file_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    payload = {'chat_id': chat_id, 'document': file_id}
    requests.post(url, json=payload)

def log_to_discord(webhook_url, message):
    payload = {"content": message}
    try:
        requests.post(webhook_url, json=payload)
    except Exception as e:
        print(f"Failed to log to Discord: {e}")

def save_movie(name, file_id):
    movies_collection.update_one(
        {'name': name},
        {'$set': {'name': name, 'file_id': file_id}},
        upsert=True
    )

def load_movies():
    movies = {}
    for doc in movies_collection.find():
        movies[doc['name']] = {'file_id': doc['file_id']}
    return movies

def rename_movie(old_name, new_name):
    movie = movies_collection.find_one({'name': old_name})
    if movie:
        movies_collection.delete_one({'name': old_name})
        movie['name'] = new_name
        movies_collection.insert_one(movie)
        return True
    return False

def delete_movie(name):
    movies_collection.delete_one({'name': name})

# Main processing function
def process_update(update):
    if 'message' not in update:
        return

    chat_id = update['message']['chat']['id']
    user_id = update['message']['from']['id']
    text = update['message'].get('text', '')
    document = update['message'].get('document')
    video = update['message'].get('video')

    # Admin uploading file
    if (document or video) and user_id == ADMIN_ID:
        file_id = document['file_id'] if document else video['file_id']
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
        return

    # Admin naming movie
    if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
        save_movie(text, TEMP_FILE_IDS[chat_id])
        send_message(chat_id, f"Movie '{text}' has been added.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie added: {text}")
        del TEMP_FILE_IDS[chat_id]
        return

    # /list_files
    if text == '/list_files' and user_id == ADMIN_ID:
        movies = load_movies()
        msg = "Stored Files:\n" + "\n".join(movies.keys()) if movies else "No files stored."
        send_message(chat_id, msg)
        return

    # /rename_file
    if text.startswith('/rename_file') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Usage: /rename_file OldName NewName")
        else:
            _, old_name, new_name = parts
            if rename_movie(old_name, new_name):
                send_message(chat_id, f"Renamed '{old_name}' to '{new_name}'.")
                log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Renamed '{old_name}' to '{new_name}'")
            else:
                send_message(chat_id, f"Movie '{old_name}' not found.")
        return

    # /delete_file
    if text.startswith('/delete_file') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /delete_file FileName")
        else:
            file_name = parts[1]
            delete_movie(file_name)
            send_message(chat_id, f"Deleted '{file_name}'.")
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Deleted movie: {file_name}")
        return

    # /get_movie_link
    if text.startswith('/get_movie_link') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /get_movie_link Movie Name")
            return
        movie_name = parts[1]
        movies = load_movies()
        if movie_name in movies:
            safe_name = movie_name.replace(" ", "_")
            movie_link = f"https://t.me/{BOT_USERNAME}?start={safe_name}"
            send_message(chat_id, f"Click here to get the movie: {movie_link}")
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Generated link for: {movie_name}")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
        return

    # /publish command
    if text.startswith('/publish') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Usage: /publish @ChannelUsername MovieName")
            return
        _, channel_username, movie_name = parts
        movie_name = movie_name.strip()

        if not channel_username.startswith('@'):
            send_message(chat_id, "Channel username must start with @")
            return

        movies = load_movies()
        if movie_name not in movies:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
            return

        file_id = movies[movie_name]['file_id']
        
        send_document_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        payload = {
            'chat_id': channel_username,
            'document': file_id,
            'caption': f"{movie_name}",
            'parse_mode': 'Markdown'
        }
        response = requests.post(send_document_url, json=payload)

        if response.status_code == 200:
            send_message(chat_id, f"Movie '{movie_name}' published to {channel_username}")
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Published '{movie_name}' to {channel_username}")
        else:
            send_message(chat_id, f"Failed to publish. Maybe bot is not admin in {channel_username}?\n\nError: {response.text}")
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Failed to publish: {response.text}")
        return

    # User clicking movie link
    if text.startswith('/start '):
        movie_name = text.replace('/start ', '').replace('_', ' ')
        movies = load_movies()
        if movie_name in movies and 'file_id' in movies[movie_name]:
            send_file(chat_id, movies[movie_name]['file_id'])
            log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"{user_id} accessed movie: {movie_name}")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
        return

# Flask routes
@app.route('/', methods=['GET'])
def home():
    return 'Bot is Running!'

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = request.get_json()
        process_update(update)
    return 'ok'

# Set webhook when starting
def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
    payload = {'url': webhook_url}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print('Webhook set successfully!')
    else:
        print('Failed to set webhook:', response.text)

if __name__ == '__main__':
    set_webhook()
    app.run(host='0.0.0.0', port=5000)