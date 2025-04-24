import os
import sys
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
MEDIA_UPLOADS = {}
REGISTERED_CHANNELS = set()

# Webhook Logger
def log_to_discord(webhook, message):
    if webhook:
        try:
            requests.post(webhook, json={"content": message})
        except Exception as e:
            print(f"Error logging to Discord: {e}")

# MongoDB Setup
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client['telegram_bot']
    movies_collection = db['movies']
    channels_collection = db['channels']
    log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.")
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ Failed to connect to MongoDB: {e}")
    raise e

# On startup
log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now online!")

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

def register_channel(channel_username):
    exists = channels_collection.find_one({"channel": channel_username})
    if not exists:
        channels_collection.insert_one({"channel": channel_username})

def get_registered_channels():
    return [doc['channel'] for doc in channels_collection.find()]

# Telegram Actions
def send_message(chat_id, text, parse_mode=None, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    if reply_markup:
        payload['reply_markup'] = reply_markup
    response = requests.post(url, json=payload)
    return response.json()

def send_media(chat_id, caption, media_file_id=None, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
    if media_file_id:
        payload['photo'] = media_file_id
    if reply_markup:
        payload['reply_markup'] = reply_markup
    return requests.post(url, json=payload)

def send_file(chat_id, file_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    payload = {'chat_id': chat_id, 'document': file_id}
    response = requests.post(url, json=payload)
    message_data = response.json()
    if message_data.get('ok'):
        file_message_id = message_data['result']['message_id']
        warning_text = (
            "❗️ *IMPORTANT* ❗️\n\n"
            "This Video / File Will Be Deleted In *30 minutes* _(Due To Copyright Issues)_\n\n"
            "📌 *Please Forward This Video / File To Somewhere Else And Start Downloading There.*"
        )
        warning_response = send_message(chat_id, warning_text, parse_mode="Markdown")
        warning_message_id = warning_response['result']['message_id']
        threading.Timer(1800, delete_message, args=[chat_id, file_message_id]).start()
        threading.Timer(1800, delete_message, args=[chat_id, warning_message_id]).start()

def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
    payload = {'chat_id': chat_id, 'message_id': message_id}
    requests.post(url, json=payload)

# USER_STATE to manage the state of each user
USER_STATE = {}

# Main update handler
def process_update(update):
    if 'message' not in update:
        return
    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    text = message.get('text', '')
    document = message.get('document')
    video = message.get('video')
    photo = message.get('photo')

    if user_id != ADMIN_ID:
        return

    if (document or video or photo):
        file_id = document['file_id'] if document else video['file_id'] if video else photo[-1]['file_id']
        MEDIA_UPLOADS[chat_id] = file_id
        send_message(chat_id, "Media uploaded successfully. Now use /send_message command to customize your post.")
        return

    if text.startswith('/send_message'):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /send_message @channel_name")
            return
        channel = parts[1].strip()
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
        r = requests.post(url, json={"chat_id": channel, "user_id": int(BOT_TOKEN.split(':')[0])})
        data = r.json()
        if data.get("ok") and data['result']['status'] in ['administrator', 'creator']:
            register_channel(channel)
            send_message(chat_id, f"Bot is an admin in {channel}. Now, send the caption for the movie post.")
            USER_STATE[user_id] = 'waiting_for_caption'  # Track state
        else:
            send_message(chat_id, f"Bot is not admin in {channel}. Add the bot as admin and try again.")
            return

    if user_id in USER_STATE and USER_STATE[user_id] == 'waiting_for_caption':
        caption = text  # Capture the caption provided by the admin
        USER_STATE[user_id] = 'waiting_for_buttons'  # Now track that it's waiting for buttons
        send_message(chat_id, "Now, send inline buttons in this format:\nText1 - URL1\nText2 - URL2\n...")
        return

    if user_id in USER_STATE and USER_STATE[user_id] == 'waiting_for_buttons':
        buttons = text  # Capture the buttons input by the admin
        USER_STATE[user_id] = 'waiting_for_preview'  # Track that it's waiting for preview
        send_message(chat_id, "Here is a preview of your post with the caption and buttons.")
        # Provide a preview of the post
        preview_caption = "🎬 *Movie Title 2025*\n🔊 Tamil Audio\n📜 English Subtitles\n⏳ Duration: 2h 42m"
        reply_markup = {"inline_keyboard": [
            [{"text": "480p", "url": "https://example.com/480p"}],
            [{"text": "720p", "url": "https://example.com/720p"}]
        ]}
        send_message(chat_id, preview_caption, reply_markup=reply_markup)
        return

    if user_id in USER_STATE and USER_STATE[user_id] == 'waiting_for_preview':
        send_message(chat_id, "Post sent to the channel.")
        USER_STATE.pop(user_id)  # Reset the state after the process is completed
        return

@app.errorhandler(Exception)
def handle_exception(error):
    # Log the error to Discord
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"⚠️ Error occurred: {str(error)}")
    return jsonify({"error": str(error)}), 500

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    try:
        update = request.get_json()
        process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)