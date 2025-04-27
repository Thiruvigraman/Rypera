import os
import requests
import signal
import sys
from flask import Flask, request
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

WEBHOOK_URL = os.getenv('WEBHOOK_URL')
MONGO_URI = os.getenv('MONGO_URI')
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')
BOT_USERNAME = os.getenv('BOT_USERNAME')
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# Flask app
app = Flask(__name__)

# Temp storage for uploaded files
TEMP_FILE_IDS = {}
# Track users
USERS = set()

# Function to log messages to Discord with an optional embed
def log_to_discord(webhook_url, message, embed=None):
    try:
        payload = {"content": message}
        if embed:
            payload["embeds"] = [embed]
        requests.post(webhook_url, json=payload)
    except Exception as e:
        print(f"Discord logging failed: {e}")

# Function to create embeds with a title, description, color, and timestamp in footer
def create_embed(title, description, color=0x00ff00):
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {
            "text": "Premium Bot"
        }
    }
    return embed

# MongoDB setup
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['telegram_bot']
    movies_collection = db['movies']
    log_to_discord(DISCORD_WEBHOOK_STATUS, "⚡ Connected to MongoDB!")
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ MongoDB connection failed:\n{e}")
    sys.exit()

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=payload)

def send_file(chat_id, file_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    payload = {'chat_id': chat_id, 'document': file_id}
    requests.post(url, json=payload)

def save_movie(name, file_id):
    movies_collection.update_one({'name': name}, {'$set': {'file_id': file_id}}, upsert=True)

def load_movies():
    movies = {}
    for doc in movies_collection.find():
        movies[doc['name']] = {'file_id': doc['file_id']}
    return movies

def rename_movie(old_name, new_name):
    movie = movies_collection.find_one({'name': old_name})
    if movie:
        movies_collection.update_one({'name': old_name}, {'$set': {'name': new_name}})
        return True
    return False

def delete_movie(name):
    movies_collection.delete_one({'name': name})

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/webhook/<token>', methods=['POST'])
def webhook(token):
    if token != BOT_TOKEN:
        return "Unauthorized", 403

    update = request.get_json()
    process_update(update)
    return "OK", 200

def process_update(update):
    if 'message' not in update:
        return

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    text = message.get('text', '')
    document = message.get('document')
    video = message.get('video')

    # Track user
    USERS.add(chat_id)

    # Admin uploading file
    if (document or video) and user_id == ADMIN_ID:
        file_id = document['file_id'] if document else video['file_id']
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
        return

    # Admin naming movie
    if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
        save_movie(text, TEMP_FILE_IDS[chat_id])
        send_message(chat_id, f"🎬 Movie '{text}' has been added.")
        embed = create_embed(
            title="🎬 Movie Added",
            description=f"Movie **{text}** has been added successfully.",
            color=0x2ecc71  # Green for success
        )
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie added: **{text}**", embed)
        del TEMP_FILE_IDS[chat_id]
        return

    # /list_files
    if text == '/list_files' and user_id == ADMIN_ID:
        movies = load_movies()
        msg = "🎞️ Stored Files:\n" + "\n".join(movies.keys()) if movies else "No files stored."
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
                send_message(chat_id, f"✏️ Renamed '{old_name}' to '{new_name}'.")
                embed = create_embed(
                    title="✏️ Movie Renamed",
                    description=f"Movie **{old_name}** has been renamed to **{new_name}**.",
                    color=0xe67e22  # Orange for renaming
                )
                log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie renamed: **{old_name}** ➔ **{new_name}**", embed)
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
            send_message(chat_id, f"🗑️ Deleted '{file_name}'.")
            embed = create_embed(
                title="❌ Movie Deleted",
                description=f"Movie **{file_name}** has been deleted.",
                color=0xe74c3c  # Red for deletion
            )
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie deleted: **{file_name}**", embed)
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
            send_message(chat_id, f"🔗 [Click here to get the movie]({movie_link})")
            embed = create_embed(
                title="🔗 Movie Link Generated",
                description=f"Link for **{movie_name}** generated.",
                color=0x3498db  # Blue for link generation
            )
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Generated link for: **{movie_name}**", embed)
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
        return

    # User clicking movie link
    if text.startswith('/start '):
        movie_name = text.replace('/start ', '').replace('_', ' ')
        movies = load_movies()
        if movie_name in movies and 'file_id' in movies[movie_name]:
            send_file(chat_id, movies[movie_name]['file_id'])
            embed = create_embed(
                title="🎥 Movie Requested",
                description=f"Movie **{movie_name}** has been successfully sent to you.",
                color=0x9b59b6  # Purple for movie request
            )
            log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"Movie accessed: **{movie_name}**", embed)
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
        return

# Handle graceful shutdown (send offline log)
def shutdown_handler(signal, frame):
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🔴 Bot went offline!")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == '__main__':
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🟢 Bot is Online and Running!")
    app.run(host="0.0.0.0", port=5000)