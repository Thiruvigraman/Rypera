import os
import sys
import signal
import requests
import logging
from flask import Flask, request
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
MONGO_URI = os.getenv('MONGO_URI')
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')

# Flask app
app = Flask(__name__)

# Temporary storage
TEMP_FILE_IDS = {}

# Discord log
def log_to_discord(webhook_url, message, embed=None):
    try:
        data = {"content": message}
        if embed:
            data["embeds"] = [embed]
        requests.post(webhook_url, json=data)
    except Exception as e:
        logger.error(f"Discord log error: {e}")

# Embed template
def create_embed(title, desc, color=0x00ff00):
    return {
        "title": title,
        "description": desc,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Premium Bot"}
    }

# MongoDB setup
def connect_mongo():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client['telegram_bot']
        movies_collection = db['movies']
        client.server_info()
        log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB Connected")
        return db, movies_collection
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ MongoDB Connection Failed:\n{e}")
        sys.exit()

db, movies_collection = connect_mongo()

# Save movie data
def save_movie(name, file_id):
    movie_link = f"/start {name}"
    if movies_collection.find_one({'name': name}):
        logger.warning(f"Movie '{name}' already exists.")
        return False
    movies_collection.update_one({'name': name}, {'$set': {'file_id': file_id, 'link': movie_link}}, upsert=True)
    return True

# Load all movie data
def load_movies():
    return {doc['name']: {'file_id': doc['file_id'], 'link': doc['link']} for doc in movies_collection.find()}

# Send a message
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={'chat_id': chat_id, 'text': text})
    if response.status_code != 200:
        logger.error(f"Failed to send message: {response.text}")

# Send a file
def send_file(chat_id, file_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    requests.post(url, data={"chat_id": chat_id, "document": file_id})

# Process Telegram updates
def process_update(update):
    if 'message' not in update:
        return

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    text = message.get('text', '')
    document = message.get('document')
    video = message.get('video')

    if user_id != ADMIN_ID:
        return

    # Admin file management
    if document or video:
        file_id = document['file_id'] if document else video['file_id']
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
        return

    # Save movie
    if chat_id in TEMP_FILE_IDS and text:
        file_id = TEMP_FILE_IDS[chat_id]
        if save_movie(text, file_id):
            send_message(chat_id, f"🎬 Movie '{text}' has been added.")
            embed = create_embed(
                title="🎬 Movie Added",
                description=f"Movie **{text}** has been added successfully.",
                color=0x2ecc71
            )
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie added: **{text}**", embed)
        else:
            send_message(chat_id, f"⚠️ Movie '{text}' already exists.")
        del TEMP_FILE_IDS[chat_id]
        return

    # List movies
    if text == "/list_movies":
        docs = movies_collection.find({}, {"_id": 0, "name": 1})
        names = [d["name"] for d in docs]
        msg = "\n".join(f"- {n}" for n in names) or "No movies found."
        send_message(chat_id, f"**Movie List:**\n{msg}")
        return

    # Rename movie
    if text.startswith("/rename_movie "):
        try:
            _, old, new = text.split(maxsplit=2)
            doc = movies_collection.find_one({"name": old})
            if not doc:
                send_message(chat_id, f"Movie '{old}' not found.")
                return
            doc["name"] = new
            doc["link"] = f"/start {new}"
            movies_collection.update_one({"name": old}, {"$set": doc})
            send_message(chat_id, f"Renamed '{old}' to '{new}'")
        except:
            send_message(chat_id, "Usage: /rename_movie <old> <new>")
        return

    # Delete movie
    if text.startswith("/delete_movie "):
        try:
            _, name = text.split(maxsplit=1)
            res = movies_collection.delete_one({"name": name})
            msg = f"Deleted '{name}'" if res.deleted_count else f"Movie '{name}' not found."
            send_message(chat_id, msg)
        except:
            send_message(chat_id, "Usage: /delete_movie <name>")
        return

    # Health check
    if text == "/health":
        try:
            movies_collection.estimated_document_count()
            send_message(chat_id, "✅ Bot is healthy.")
        except:
            send_message(chat_id, "❌ MongoDB connection error.")
        return

    # User file access via /start <movie_name>
    if text.startswith("/start "):
        try:
            _, movie_name = text.split(maxsplit=1)
            movie = movies_collection.find_one({"name": movie_name})
            if movie:
                send_file(chat_id, movie["file_id"])
                log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"User {user_id} accessed '{movie_name}'")
            else:
                send_message(chat_id, "Movie not found.")
        except:
            send_message(chat_id, "Invalid request.")
    else:
        # Ignore all other messages from users
        if user_id != ADMIN_ID:
            send_message(chat_id, "Access denied.")

# Root route for health check
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200

# Webhook endpoint
@app.route('/webhook/<token>', methods=['POST'])
def webhook(token):
    if token != BOT_TOKEN:
        return "Unauthorized", 403
    update = request.get_json()
    process_update(update)
    return "OK", 200

# Graceful shutdown
def shutdown_handler(signal_num, frame):
    embed = create_embed(
        title="🔴 Bot Offline",
        description="The bot has gone offline.",
        color=0xe74c3c
    )
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🔴 Bot went offline!", embed)
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# Start the app
if __name__ == '__main__':
    embed = create_embed(
        title="🟢 Bot Online",
        description="The bot is online and ready to use!",
        color=0x2ecc71
    )
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🟢 Bot is Online and Running!", embed)
    app.run(host="0.0.0.0", port=5000)