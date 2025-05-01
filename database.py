#database.py
from pymongo import MongoClient
from typing import Dict, Any, List
from config import MONGODB_URI
from bot import send_message
from utils import log_to_discord, DISCORD_WEBHOOK_STATUS
from datetime import datetime, timedelta
import pytz

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000, maxPoolSize=3)
db = client['telegram_bot']

def connect_db():
    """Connect to MongoDB and create indexes."""
    try:
        client.admin.command('ping')
        db['movies'].create_index("name", unique=True)
        db['deletions'].create_index("delete_at")
        log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.", critical=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[connect_db] Failed: {str(e)}", critical=True)
        raise

def close_db():
    """Close MongoDB connection."""
    try:
        client.close()
        log_to_discord(DISCORD_WEBHOOK_STATUS, "[close_db] MongoDB connection closed.", critical=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[close_db] Error: {str(e)}", critical=True)

def save_movie(file_id: str, name: str, chat_id: int) -> None:
    """Save movie to database and schedule deletion."""
    try:
        ist = pytz.timezone('Asia/Kolkata')
        delete_at = datetime.now(ist) + timedelta(minutes=30)
        db['movies'].insert_one({"file_id": file_id, "name": name, "chat_id": chat_id})
        db['deletions'].insert_one({"file_id": file_id, "chat_id": chat_id, "delete_at": delete_at})
        send_message(chat_id, f"Movie '{name}' will be deleted at {delete_at.strftime('%Y-%m-%d %H:%M:%S %Z')}.")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[save_movie] Error: {str(e)}", critical=True)
        send_message(chat_id, "Failed to save movie.")

def get_all_movies() -> List[Dict[str, Any]]:
    """Get all movies."""
    try:
        return list(db['movies'].find().sort("name"))
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_all_movies] Error: {str(e)}", critical=True)
        return []

def update_movie_name(old_name: str, new_name: str) -> bool:
    """Update movie name."""
    try:
        result = db['movies'].update_one({"name": old_name}, {"$set": {"name": new_name}})
        return result.modified_count > 0
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[update_movie_name] Error: {str(e)}", critical=True)
        return False

def delete_movie(name: str) -> bool:
    """Delete movie and its deletion schedule."""
    try:
        movie = db['movies'].find_one({"name": name})
        if not movie:
            return False
        db['movies'].delete_one({"name": name})
        db['deletions'].delete_one({"file_id": movie['file_id']})
        return True
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_movie] Error: {str(e)}", critical=True)
        return False

def get_movie_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get movie by name."""
    try:
        return db['movies'].find_one({"name": name})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie_by_name] Error: {str(e)}", critical=True)
        return None

def track_user(user_id: int) -> None:
    """Track user in database."""
    try:
        db['users'].update_one(
            {"user_id": user_id},
            {"$set": {"last_seen": datetime.now(pytz.timezone('Asia/Kolkata'))}},
            upsert=True
        )
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[track_user] Error: {str(e)}", critical=True)

def get_all_users() -> List[Dict[str, Any]]:
    """Get all users."""
    try:
        return list(db['users'].find())
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_all_users] Error: {str(e)}", critical=True)
        return []

def process_scheduled_deletions() -> None:
    """Process scheduled deletions."""
    try:
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        deletions = db['deletions'].find({"delete_at": {"$lte": now}}).limit(100)
        for deletion in deletions:
            try:
                file_id = deletion['file_id']
                chat_id = deletion['chat_id']
                movie = db['movies'].find_one({"file_id": file_id})
                if movie:
                    db['movies'].delete_one({"file_id": file_id})
                    send_message(chat_id, f"Movie '{movie['name']}' has been deleted as scheduled.")
                db['deletions'].delete_one({"_id": deletion['_id']})
            except Exception as e:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Error processing deletion: {str(e)}", critical=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Error: {str(e)}", critical=True)