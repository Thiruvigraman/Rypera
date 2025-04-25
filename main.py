import os
import requests
import threading
import atexit
from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

# ENV Variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
BOT_USERNAME = os.getenv('BOT_USERNAME')
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')
MONGODB_URI = os.getenv('MONGODB_URI')

if not BOT_TOKEN or not ADMIN_ID or not BOT_USERNAME or not MONGODB_URI:
    raise ValueError("Missing environment variables")

ADMIN_ID = int(ADMIN_ID)
TEMP_FILE_IDS = {}

# Webhook Logger
def log_to_discord(webhook, message):
    if webhook:
        try:
            requests.post(webhook, json={"content": message})
        except:
            pass

# MongoDB Setup
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Force connection to test
    db = client['telegram_bot']
    movies_collection = db['movies']
    channels_collection = db['channels']  # For storing registered channels
    log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.")
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ Failed to connect to MongoDB: {e}")
    raise e

# On startup
log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now online!")

# On exit
def on_exit():
    log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now offline.")
atexit.register(on_exit)

# MongoDB Actions
def load_movies():
    movies = {}
    for doc in movies_collection.find():
        movies[doc['name']] = {"file_id": doc['file_id']}
    return movies

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

def register_channel(channel_id, channel_name):
    channels_collection.update_one({"channel_id": channel_id}, {"$set": {"channel_name": channel_name}}, upsert=True)

def check_if_admin(channel_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getChatAdministrators'
    payload = {'chat_id': channel_id}
    response = requests.post(url, json=payload).json()

    if response.get('ok') and 'result' in response:
        for admin in response['result']:
            if admin['user']['id'] == ADMIN_ID:
                return True
    return False

# Telegram Actions
def send_message(chat_id, text, parse_mode=None):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    response = requests.post(url, json=payload)
    return response.json()

# Main update handler
def process_update(update):
    if 'message' not in update:
        return

    chat_id = update['message']['chat']['id']
    user_id = update['message']['from']['id']
    text = update['message'].get('text', '')

    # Admin registering channel
    if text.startswith('/registerchannel') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /registerchannel ChannelID")
            return
        channel_id = parts[1]
        
        # Check if the bot is an admin in the channel
        if check_if_admin(channel_id):
            channel_name = update['message']['chat']['username']
            register_channel(channel_id, channel_name)
            send_message(chat_id, f"Channel '{channel_name}' has been successfully registered.")
        else:
            send_message(chat_id, f"The bot is not an admin in the channel '{channel_id}'. Please make it an admin first.")
        return

    # Other bot functionalities like /publish, /get_movie_link, etc., follow here...
    # Example:
    # if text == "/publish":
    #     # Handle publishing logic using channels stored in MongoDB

# Webhook Endpoint
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    try:
        update = request.get_json()
        process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# Run
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)