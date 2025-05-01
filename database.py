# database.py
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
from typing import Optional, Dict
from config import MONGODB_URI, DISCORD_WEBHOOK_STATUS
from utils import log_to_discord

client: Optional[MongoClient] = None
db = None
movies_collection = None

def connect_db() -> None:
    """Connect to MongoDB and initialize collections."""
    global client, db, movies_collection
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  # Force connection check
        db = client['telegram_bot']
        movies_collection = db['movies']
        log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.")
    except ServerSelectionTimeoutError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ MongoDB timeout: {e}")
        raise
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ Failed to connect to MongoDB: {e}")
        raise

def close_db() -> None:
    """Close MongoDB client if connected."""
    if client:
        client.close()

def load_movies() -> Dict[str, Dict[str, str]]:
    """Return all movies as a dict: {name: {file_id}}"""
    try:
        return {doc['name']: {"file_id": doc['file_id']} for doc in movies_collection.find()]
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[load_movies] DB error: {e}")
        return {}

def save_movie(name: str, file_id: str) -> None:
    """Insert or update a movie record."""
    try:
        movies_collection.update_one(
            {"name": name},
            {"$set": {"file_id": file_id}},
            upsert=True
        )
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[save_movie] DB error: {e}")

def delete_movie(name: str) -> None:
    """Delete a movie by name."""
    try:
        movies_collection.delete_one({"name": name})
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_movie] DB error: {e}")

def rename_movie(old_name: str, new_name: str) -> bool:
    """Rename a movie by creating a new entry and deleting the old one."""
    try:
        movie = movies_collection.find_one({"name": old_name})
        if movie:
            save_movie(new_name, movie['file_id'])
            delete_movie(old_name)
            return True
    except PyMongoError as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_movie] DB error: {e}")
    return False