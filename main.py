import os import requests import threading import atexit from flask import Flask, request, jsonify from pymongo import MongoClient from dotenv import load_dotenv

Load environment variables

load_dotenv()

app = Flask(name)

@app.route("/", methods=["GET"]) def home(): return "Bot is running!", 200

ENV Variables

BOT_TOKEN = os.getenv('BOT_TOKEN') ADMIN_ID = os.getenv('ADMIN_ID') BOT_USERNAME = os.getenv('BOT_USERNAME') DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS') DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS') DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS') MONGODB_URI = os.getenv('MONGODB_URI')

if not BOT_TOKEN or not ADMIN_ID or not BOT_USERNAME or not MONGODB_URI: raise ValueError("Missing environment variables")

ADMIN_ID = int(ADMIN_ID) TEMP_FILE_IDS = {} TEMP_CHANNELS = {} TEMP_MESSAGES = {}

Webhook Logger

def log_to_discord(webhook, message): if webhook: try: requests.post(webhook, json={"content": message}) except: pass

MongoDB Setup

try: client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000) client.server_info() db = client['telegram_bot'] movies_collection = db['movies'] channels_collection = db['channels'] log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.") except Exception as e: log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ Failed to connect to MongoDB: {e}") raise e

log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now online!")

def on_exit(): log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is now offline.") atexit.register(on_exit)

MongoDB Actions

def load_movies(): return {doc['name']: {"file_id": doc['file_id']} for doc in movies_collection.find()}

def save_movie(name, file_id): movies_collection.update_one({"name": name}, {"$set": {"file_id": file_id}}, upsert=True)

def delete_movie(name): movies_collection.delete_one({"name": name})

def rename_movie(old_name, new_name): movie = movies_collection.find_one({"name": old_name}) if movie: delete_movie(old_name) save_movie(new_name, movie['file_id']) return True return False

def store_channel(chat_id, username): channels_collection.update_one({"chat_id": chat_id}, {"$set": {"username": username}}, upsert=True)

def get_all_channels(): return [doc['chat_id'] for doc in channels_collection.find()]

Telegram Actions

def send_message(chat_id, text, parse_mode=None, buttons=None): url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage' payload = {'chat_id': chat_id, 'text': text} if parse_mode: payload['parse_mode'] = parse_mode if buttons: payload['reply_markup'] = {"inline_keyboard": buttons} response = requests.post(url, json=payload) return response.json()

def send_file(chat_id, file_id, caption=None): url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument' payload = {'chat_id': chat_id, 'document': file_id} if caption: payload['caption'] = caption response = requests.post(url, json=payload) if response.ok: file_message_id = response.json()['result']['message_id'] warning = send_message(chat_id, "❗️ IMPORTANT ❗️\n\nThis File Will Be Deleted In 30 minutes.\n\nPlease forward and start downloading soon.", parse_mode="Markdown") warn_msg_id = warning['result']['message_id'] threading.Timer(1800, delete_message, args=[chat_id, file_message_id]).start() threading.Timer(1800, delete_message, args=[chat_id, warn_msg_id]).start()

def delete_message(chat_id, message_id): url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage' requests.post(url, json={'chat_id': chat_id, 'message_id': message_id})

def check_admin_rights(chat_id): url = f'https://api.telegram.org/bot{BOT_TOKEN}/getChatMember' params = {'chat_id': chat_id, 'user_id': f"{BOT_TOKEN.split(':')[0]}"} response = requests.get(url, params=params) result = response.json() return result.get("result", {}).get("status") in ["administrator", "creator"]

Main update handler

def process_update(update): if 'message' not in update: return

msg = update['message']
chat_id = msg['chat']['id']
user_id = msg['from']['id']
text = msg.get('text', '')
document = msg.get('document')
video = msg.get('video')
photo = msg.get('photo')

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

if text == '/list_files' and user_id == ADMIN_ID:
    movies = load_movies()
    msg = "Stored Files:\n" + "\n".join(movies.keys()) if movies else "No files stored."
    send_message(chat_id, msg)
    return

if text.startswith('/rename_file') and user_id == ADMIN_ID:
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        send_message(chat_id, "Usage: /rename_file OldName NewName")
    else:
        _, old, new = parts
        if rename_movie(old, new):
            send_message(chat_id, f"Renamed '{old}' to '{new}'")
        else:
            send_message(chat_id, f"Movie '{old}' not found")
    return

if text.startswith('/delete_file') and user_id == ADMIN_ID:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /delete_file FileName")
    else:
        name = parts[1]
        delete_movie(name)
        send_message(chat_id, f"Deleted '{name}'")
    return

if text.startswith('/get_movie_link') and user_id == ADMIN_ID:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /get_movie_link Movie Name")
        return
    name = parts[1]
    movies = load_movies()
    if name in movies:
        safe = name.replace(" ", "_")
        link = f"https://t.me/{BOT_USERNAME}?start={safe}"
        send_message(chat_id, f"Click here: {link}")
    else:
        send_message(chat_id, f"Movie '{name}' not found")
    return

if text.startswith('/send_message') and user_id == ADMIN_ID:
    TEMP_CHANNELS[chat_id] = {'step': 1, 'data': {}}
    send_message(chat_id, "Send the @channel username:")
    return

if chat_id in TEMP_CHANNELS:
    step = TEMP_CHANNELS[chat_id]['step']
    data = TEMP_CHANNELS[chat_id]['data']

    if step == 1:
        channel_username = text.strip()
        resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat?chat_id={channel_username}")
        if resp.ok:
            chat_data = resp.json()['result']
            if check_admin_rights(chat_data['id']):
                store_channel(chat_data['id'], channel_username)
                data['chat_id'] = chat_data['id']
                TEMP_CHANNELS[chat_id]['step'] = 2
                send_message(chat_id, "Send the movie details (Markdown supported):")
            else:
                send_message(chat_id, "Bot is not admin in that channel.")
        else:
            send_message(chat_id, "Invalid channel username")
        return

    elif step == 2:
        data['text'] = text
        TEMP_CHANNELS[chat_id]['step'] = 3
        send_message(chat_id, "Now send media (optional) or type SKIP:")
        return

    elif step == 3:
        if document:
            data['media_file_id'] = document['file_id']
        elif photo:
            data['media_file_id'] = photo[-1]['file_id']
        elif text.strip().lower() == "skip":
            data['media_file_id'] = None
        else:
            send_message(chat_id, "Send valid media or type SKIP")
            return
        TEMP_CHANNELS[chat_id]['step'] = 4
        send_message(chat_id, "Send inline buttons in this format:\nName1 - link1 | Name2 - link2")
        return

    elif step == 4:
        button_parts = text.split('|')
        buttons = []
        for part in button_parts:
            if '-' in part:
                name, link = part.strip().split('-', 1)
                buttons.append([{"text": name.strip(), "url": link.strip()}])
        data['buttons'] = buttons
        if data.get('media_file_id'):
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
            payload = {
                'chat_id': data['chat_id'],
                'photo': data['media_file_id'],
                'caption': data['text'],
                'parse_mode': 'Markdown',
                'reply_markup': {"inline_keyboard": buttons}
            }
            requests.post(url, json=payload)
        else:
            send_message(data['chat_id'], data['text'], parse_mode="Markdown", buttons=buttons)
        send_message(chat_id, "Message sent to channel!")
        del TEMP_CHANNELS[chat_id]
        return

if text.startswith('/start '):
    name = text.replace('/start ', '').replace('_', ' ')
    movies = load_movies()
    if name in movies:
        send_file(chat_id, movies[name]['file_id'])
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"{user_id} accessed movie: {name}")
    else:
        send_message(chat_id, f"Movie '{name}' not found")
    return

@app.route(f'/{BOT_TOKEN}', methods=['POST']) def handle_webhook(): try: update = request.get_json() process_update(update) return jsonify(success=True) except Exception as e: log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error: {e}") return jsonify({"error": str(e)}), 500

if name == 'main': app.run(host='0.0.0.0', port=8080)

