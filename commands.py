import os
import sys
import logging
import requests
from pymongo import MongoClient
from discord_webhook import log_to_discord, create_embed

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
MONGO_URI = os.getenv('MONGO_URI')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')

TEMP_FILE_IDS = {}
movies_collection = None

def connect_mongo():
    global movies_collection
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client['telegram_bot']
        movies_collection = db['movies']
        client.server_info()
        return db, movies_collection
    except Exception as e:
        embed = create_embed("âŒ MongoDB Connection Failed", str(e), color=0xe74c3c)
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), "âŒ MongoDB Connection Error", embed)
        sys.exit()

def save_movie(name, file_id):
    movie_link = f"/start {name}"
    if movies_collection.find_one({'name': name}):
        logger.warning(f"Movie '{name}' already exists.")
        return False
    movies_collection.update_one({'name': name}, {'$set': {'file_id': file_id, 'link': movie_link}}, upsert=True)
    return True

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json={'chat_id': chat_id, 'text': text}, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to send message: {response.text}")

def send_file(chat_id, file_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        response = requests.post(url, data={"chat_id": chat_id, "document": file_id})
        if response.status_code != 200:
            logger.error(f"Failed to send file: {response.text}")
    except Exception as e:
        logger.error(f"Error sending file: {str(e)}")

def process_update(update):
    if 'message' not in update:
        return

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    text = message.get('text', '')
    document = message.get('document')
    video = message.get('video')

    if user_id != ADMIN_ID and not text.startswith("/start "):
        return

    if document or video:
        file_id = document['file_id'] if document else video['file_id']
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
        return

    if chat_id in TEMP_FILE_IDS and text:
        file_id = TEMP_FILE_IDS[chat_id]
        if save_movie(text, file_id):
            send_message(chat_id, f"ðŸŽ¬ Movie '{text}' has been added.")
            embed = create_embed(
                title="ðŸŽ¬ Movie Added",
                description=f"Movie **{text}** has been added successfully.",
                color=0x2ecc71
            )
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie added: **{text}**", embed)
        else:
            send_message(chat_id, f"âš ï¸ Movie '{text}' already exists.")
        del TEMP_FILE_IDS[chat_id]
        return

    if text == "/list_movies":
        docs = movies_collection.find({}, {"_id": 0, "name": 1})
        names = [d["name"] for d in docs]
        msg = "\n".join(f"- {n}" for n in names) or "No movies found."
        send_message(chat_id, f"**Movie List:**\n{msg}")
        return

    if text.startswith("/rename_movie "):
        try:
            _, old, new = text.split(maxsplit=2)
            doc = movies_collection.find_one({"name": old})
            if not doc:
                send_message(chat_id, f"Movie '{old}' not found.")
                return
            if movies_collection.find_one({"name": new}):
                send_message(chat_id, f"Movie '{new}' already exists.")
                return
            doc["name"] = new
            doc["link"] = f"/start {new}"
            movies_collection.update_one({"name": old}, {"$set": doc})
            send_message(chat_id, f"Renamed '{old}' to '{new}'")
        except Exception as e:
            logger.error(str(e))
            send_message(chat_id, "Usage: /rename_movie <old> <new>")
        return

    if text.startswith("/delete_movie "):
        try:
            _, name = text.split(maxsplit=1)
            res = movies_collection.delete_one({"name": name})
            msg = f"Deleted '{name}'" if res.deleted_count else f"Movie '{name}' not found."
            send_message(chat_id, msg)
        except:
            send_message(chat_id, "Usage: /delete_movie <name>")
        return

    if text == "/health":
        try:
            movies_collection.estimated_document_count()
            send_message(chat_id, "âœ… Bot is healthy.")
        except:
            send_message(chat_id, "âŒ MongoDB connection error.")
        return

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
        if user_id != ADMIN_ID:
            send_message(chat_id, "Access denied.")