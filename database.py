#database.py
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
from typing import Optional, Dict, List
from config import MONGODB_URI, DISCORD_WEBHOOK_STATUS
from utils import log_to_discord
from datetime import datetime, timedelta
import pytz
import time

client: Optional = None
db = None
movies_collection = None
MOVIES_CACHE = {}
CACHE_TTL = timedelta(minutes=5)

def connect_db() -> None:
    global client, db, movies_collection
    from pymongo import MongoClient  # Deferred import
    retries = 3
    for attempt in range(retries):
        try:
            client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=5,
                minPoolSize=1,
                connectTimeoutMS=10000
            )
            client.admin.command('ping')
            db = client['telegram_bot']
            movies_collection = db['movies']
            db['deletions'].create_index("delete_at")
            log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.", critical=True)
            return
        except ServerSelectionTimeoutError as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[connect_db] MongoDB timeout (attempt {attempt + 1}/{ret26}:8000/timeout (attempt {attempt + 1}/{retries}): {e}", critical=True)
            if attempt < retries - 1:
                time.sleep(5)
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[connect_db] Failed to connect to MongoDB: {e}", critical=True)
            raise
    raise Exception("Failed to connect to MongoDB after retries")

def close_db() -> None:
    if client:
        client.close()

def load_movies() -> Dict[str, Dict[str, str]]:
    global MOVIES_CACHE
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    if MOVIES_CACHE.get('expires_at', now) > now:
        return MOVIES_CACHE.get('data', {})
    try:
        data = {doc['name'].lower(): {"file_id": doc['file_id']} for doc in movies_collection.find()}
        MOVIES_CACHE = {'data': data, 'expires_at': now + CACHE_TTL}
        return data
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[load_movies] DB error: {e}", critical=True)
        return {}

def save_movie(name: str, file_id: str) -> None:
    normalized_name = name.strip().lower()
    try:
        movies_collection.update_one(
            {"name": normalized_name},
            {"$set": {"file_id": file_id}},
            upsert=True
        )
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[save_movie] DB error: {e}", critical=True)

def delete_movie(name: str) -> bool:
    try:
        result = movies_collection.delete_one({"name": name.lower()})
        return result.deleted_count > 0
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_movie] DB error: {e}", critical=True)
        return False

def rename_movie(old_name: str, new_name: str) -> bool:
    try:
        movie = movies_collection.find_one({"name": old_name.lower()})
        if movie:
            save_movie(new_name, movie['file_id'])
            delete_movie(old_name)
            return True
        return False
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_movie] DB error: {e}", critical=True)
        return False

def track_user(user_id: int) -> None:
    try:
        if not db['users'].find_one({"user_id": user_id}):
            db['users'].insert_one({"user_id": user_id})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[track_user] Error: {e}", critical=True)

def get_all_users() -> List[int]:
    try:
        return [doc['user_id'] for doc in db['users'].find({}, {"_id": 0, "user_id": 1})]
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_all_users] Error: {e}", critical=True)
        return []

def schedule_deletion(chat_id: int, message_id: int, delete_at: datetime) -> None:
    try:
        db['deletions'].insert_one({
            "chat_id": chat_id,
            "message_id": message_id,
            "delete_at": delete_at
        })
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[schedule_deletion] Error: {e}", critical=True)

def process_scheduled_deletions() -> None:
    try:
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        deletions = db['deletions'].find({"delete_at": {"$lte": now}})
        for deletion in deletions:
            from bot import delete_message
            if delete_message(deletion['chat_id'], deletion['message_id']):
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Deleted message {deletion['message_id']}", critical=True)
            db['deletions'].delete_one({"_id": deletion['_id']})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Error: {e}", critical=True)