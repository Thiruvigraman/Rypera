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
MEDIA_UPLOADS = {}
REGISTERED_CHANNELS = set()

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
            caption = (
                "🎬 *𝐕𝐞𝐞𝐫𝐚 𝐃𝐡𝐞𝐞𝐫𝐚 𝐒𝐨𝐨𝐫𝐚𝐧 𝟐𝟎𝟐𝟓*\n"
                "🔊 Tamil Audio\n📜 English Subtitles\n⏳ Duration: 2h 42m 08s\n\n"
                "📥 *Download Links:*"
            )
            buttons = [
                [
                    {"text": "480p", "url": "https://t.me/Vanmam_thavir_bot?start=Veera_dheera_sooran_pt2_tam_480p"},
                    {"text": "720p", "url": "https://t.me/Vanmam_thavir_bot?start=Veera_dheera_sooran_pt2_tam_720p"},
                ],
                [
                    {"text": "1080p", "url": "https://t.me/Vanmam_thavir_bot?start=Veera_dheera_sooran_pt2_tam_1080p"},
                    {"text": "HDRip", "url": "https://t.me/Vanmam_thavir_bot?start=Veera_dheera_sooran_pt2_tam_hdrip"},
                ]
            ]
            reply_markup = {"inline_keyboard": buttons}
            media_id = MEDIA_UPLOADS.pop(chat_id, None)
            if media_id:
                send_media(channel, caption, media_id, reply_markup)
            else:
                send_message(channel, caption, parse_mode="Markdown", reply_markup=reply_markup)
            send_message(chat_id, f"Message sent to {channel}")
        else:
            send_message(chat_id, f"Bot is not admin in {channel}. Add the bot as admin and try again.")
        return

    if (document or video) and user_id == ADMIN_ID:
        file_id = document['file_id'] if document else video['file_id']
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
        return

    if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
        save_movie(text, TEMP_FILE_IDS[chat_id])
        send_message(chat_id, f"Movie '{text}' has been added.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie added: {text}")
        del TEMP_FILE_IDS[chat_id]
        return

    if text == '/list_files':
        movies = load_movies()
        msg = "Stored Files:\n" + "\n".join(movies.keys()) if movies else "No files stored."
        send_message(chat_id, msg)
        return

    if text.startswith('/rename_file'):
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

    if text.startswith('/delete_file'):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /delete_file FileName")
        else:
            file_name = parts[1]
            delete_movie(file_name)
            send_message(chat_id, f"Deleted '{file_name}'.")
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Deleted movie: {file_name}")
        return

    if text.startswith('/get_movie_link'):
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

    if text.startswith('/start '):
        movie_name = text.replace('/start ', '').replace('_', ' ')
        movies = load_movies()
        if movie_name in movies and 'file_id' in movies[movie_name]:
            send_file(chat_id, movies[movie_name]['file_id'])
            log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"{user_id} accessed movie: {movie_name}")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
        return

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