import os
import requests
import signal
import sys
from flask import Flask, request
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
import threading

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

# Temp storage for uploaded files and warning messages
TEMP_FILE_IDS = {}
TEMP_WARNING_IDS = {}

# MongoDB setup
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['telegram_bot']
    movies_collection = db['movies']
    log_to_discord(DISCORD_WEBHOOK_STATUS, "⚡ Connected to MongoDB!")
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ MongoDB connection failed:\n{e}")
    sys.exit()

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

# Function to send messages
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    response = requests.post(url, json=payload)
    return response.json()

# Function to save movie data in MongoDB
def save_movie(name, file_id):
    movies_collection.update_one({'name': name}, {'$set': {'file_id': file_id}}, upsert=True)

# Function to load movie data from MongoDB
def load_movies():
    movies = {}
    for doc in movies_collection.find():
        movies[doc['name']] = {'file_id': doc['file_id']}
    return movies

# Handle file uploads and send warning message when file is sent to user
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
    if user_id != ADMIN_ID:
        return  # Ignore messages from non-admin users

    # Admin uploading a file (document or video)
    if document or video:
        file_id = document['file_id'] if document else video['file_id']
        TEMP_FILE_IDS[chat_id] = file_id

        # Ask admin for a movie name after file upload
        send_message(chat_id, "Send the name of this movie to store it:")
        return

    # Admin naming the movie
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

    # List movies command
    if text == '/list_files' and user_id == ADMIN_ID:
        movies = load_movies()
        msg = "🎞️ Stored Files:\n" + "\n".join(movies.keys()) if movies else "No files stored."
        send_message(chat_id, msg)
        return

    # User clicking a link to get a movie
    if text.startswith('/start '):
        movie_name = text.split(' ')[1]
        movie = load_movies().get(movie_name)

        if movie:
            file_id = movie['file_id']
            # Send the movie file to the user
            response = send_file_to_user(chat_id, file_id)
            if response:
                # Send warning message when file is actually sent to the user
                send_warning_message(chat_id)
            return

# Function to send the file to the user
def send_file_to_user(chat_id, file_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    payload = {'chat_id': chat_id, 'document': file_id}
    response = requests.post(url, data=payload)
    return response.json()  # This is the response from the Telegram API

# Function to send warning message to the user
def send_warning_message(chat_id):
    warning_message = "⚠️ This file will be deleted in 15 minutes. Please forward it to somewhere and start downloading⚠️."
    send_message(chat_id, warning_message)

    # Track the warning message for deletion after 15 minutes
    TEMP_WARNING_IDS[chat_id] = warning_message
    threading.Timer(900, delete_warning_message, [chat_id]).start()

# Function to delete warning message after 15 minutes
def delete_warning_message(chat_id):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
        payload = {'chat_id': chat_id, 'message_id': TEMP_WARNING_IDS.get(chat_id)}
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error deleting warning message: {e}")

# Function to handle graceful shutdown
def shutdown_handler(signal, frame):
    try:
        embed = create_embed(
            title="🔴 Bot Offline",
            description="The bot has gone offline. Please check the server.",
            color=0xe74c3c  # Red for offline
        )
        log_to_discord(DISCORD_WEBHOOK_STATUS, "🔴 Bot went offline!", embed)
    except Exception as e:
        embed = create_embed(
            title="🔴 Bot Offline",
            description=f"The bot went offline due to an error: {e}",
            color=0xe74c3c  # Red for offline
        )
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"🔴 Bot went offline due to error: {e}", embed)
    sys.exit(0)

# Register signal handlers for shutdown
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == '__main__':
    embed = create_embed(
        title="🟢 Bot Online",
        description="The bot is online and ready to use!",
        color=0x2ecc71  # Green for online
    )
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🟢 Bot is Online and Running!", embed)
    app.run(host="0.0.0.0", port=5000)