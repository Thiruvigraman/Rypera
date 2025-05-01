#database.py
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
from typing import Optional, Dict, List
from config import MONGODB_URI, DISCORD_WEBHOOK_STATUS
from utils import log_to_discord
import time

client: Optional[MongoClient] = None
db = None
movies_collection = None

def connect_db() -> None:
    global client, db, movies_collection
    retries = 3
    for attempt in range(retries):
        try:
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            client.server_info()  # Test connection
            db = client['telegram_bot']
            movies_collection = db['movies']
            log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.")
            return
        except ServerSelectionTimeoutError as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[connect_db] MongoDB timeout (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(5)  # Wait before retrying
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[connect_db] Failed to connect to MongoDB: {e}")
            raise
    raise Exception("Failed to connect to MongoDB after retries")

def close_db() -> None:
    if client:
        client.close()

def load_movies() -> Dict[str, Dict[str, str]]:
    try:
        return {doc['name']: {"file_id": doc['file_id']} for doc in movies_collection.find()}
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[load_movies] DB error: {e}")
        return {}

def save_movie(name: str, file_id: str) -> None:
    try:
        movies_collection.update_one(
            {"name": name},
            {"$set": {"file_id": file_id}},
            upsert=True
        )
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[save_movie] DB error: {e}")

def delete_movie(name: str) -> None:
    try:
        movies_collection.delete_one({"name": name})
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_movie] DB error: {e}")

def rename_movie(old_name: str, new_name: str) -> bool:
    try:
        movie = movies_collection.find_one({"name": old_name})
        if movie:
            save_movie(new_name, movie['file_id'])
            delete_movie(old_name)
            return True
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_movie] DB error: {e}")
    return False

def track_user(user_id: int) -> None:
    try:
        db['users'].update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[track_user] Error: {e}")

def get_all_users() -> List[int]:
    try:
        return [doc['user_id'] for doc in db['users'].find({}, {"_id": 0, "user_id": 1})]
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_all_users] Error: {e}")
        return []