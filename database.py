#database.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from typing import Dict, Any, List, Optional
from config import MONGODB_URI, DISCORD_WEBHOOK_STATUS, ADMIN_ID
from utils import log_to_discord
from bot import send_message
from datetime import datetime, timedelta
import pytz
import time
import traceback

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000, maxPoolSize=20, waitQueueTimeoutMS=5000)
db = client['telegram_bot']

def connect_db(max_retries=3, retry_delay=5):
    """Connect to MongoDB with retries and create indexes."""
    for attempt in range(max_retries):
        try:
            client.admin.command('ping')
            db['movies'].create_index("name", unique=True)
            db['deletions'].create_index("delete_at")
            db['temp_file_ids'].create_index("chat_id", unique=True)
            log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.")
            cleanup_overdue_deletions()
            return
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[connect_db] Attempt {attempt + 1} failed: {str(e)}", critical=True)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[connect_db] Failed after {max_retries} attempts.", critical=True)
    raise ConnectionFailure("Could not connect to MongoDB")

def cleanup_overdue_deletions():
    """Remove overdue deletion records on startup."""
    try:
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        result = db['deletions'].delete_many({"delete_at": {"$lte": now}})
        deleted_count = result.deleted_count
        if deleted_count > 0:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[cleanup_overdue_deletions] Removed {deleted_count} overdue deletion records.")
        else:
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[cleanup_overdue_deletions] No overdue deletion records found.")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[cleanup_overdue_deletions] Error: {str(e)}", critical=True)

def close_db():
    """Close MongoDB connection."""
    try:
        client.close()
        log_to_discord(DISCORD_WEBHOOK_STATUS, "[close_db] MongoDB connection closed.")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[close_db] Error: {str(e)}", critical=True)

def save_movie(file_id: str, name: str, chat_id: int) -> None:
    """Save movie to database; no deletion scheduling (admin-only uploads)."""
    try:
        db['movies'].insert_one({"file_id": file_id, "name": name.lower(), "chat_id": chat_id})
        send_message(chat_id, f"Movie '{name}' stored successfully (no deletion scheduled).")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[save_movie] Stored movie '{name}' for admin chat {chat_id} (no deletion).")
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
        result = db['movies'].update_one({"name": old_name.lower()}, {"$set": {"name": new_name.lower()}})
        return result.modified_count > 0
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[update_movie_name] Error: {str(e)}", critical=True)
        return False

def delete_movie(name: str) -> bool:
    """Delete movie and its deletion schedule."""
    try:
        movie = db['movies'].find_one({"name": name.lower()})
        if not movie:
            return False
        file_id = movie['file_id']
        db['movies'].delete_one({"name": name.lower()})
        db['deletions'].delete_one({"file_id": file_id})
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_movie] Deleted movie '{name}' and its deletion schedule (file_id: {file_id}).")
        return True
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_movie] Error: {str(e)}", critical=True)
        return False

def get_movie_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get movie by name."""
    try:
        return db['movies'].find_one({"name": name.lower()})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie_by_name] Error: {str(e)}", critical=True)
        return None

def save_temp_file_id(chat_id: int, file_id: str) -> None:
    """Save temporary file ID to database."""
    try:
        db['temp_file_ids'].update_one(
            {"chat_id": chat_id},
            {"$set": {"file_id": file_id, "created_at": datetime.now(pytz.timezone('Asia+Kolkata'))}},
            upsert=True
        )
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[save_temp_file_id] Error: {str(e)}", critical=True)

def get_temp_file_id(chat_id: int) -> Optional[str]:
    """Get temporary file ID from database."""
    try:
        doc = db['temp_file_ids'].find_one({"chat_id": chat_id})
        return doc['file_id'] if doc else None
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_temp_file_id] Error: {str(e)}", critical=True)
        return None

def delete_temp_file_id(chat_id: int) -> None:
    """Delete temporary file ID from database."""
    try:
        db['temp_file_ids'].delete_one({"chat_id": chat_id})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_temp_file_id] Error: {str(e)}", critical=True)

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
    """Process any existing scheduled deletions (legacy records)."""
    import traceback  # Explicit import to prevent NameError
    try:
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        deletions = db['deletions'].find({"delete_at": {"$lte": now}}).limit(100)
        deletion_ops = []
        movie_ops = []
        processed_count = 0

        for deletion in deletions:
            file_id = deletion.get('file_id')
            chat_id = deletion.get('chat_id')
            deletion_id = deletion.get('_id')
            processed_count += 1
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Processing deletion: file_id={file_id}, chat_id={chat_id}, deletion_id={deletion_id}, delete_at={deletion.get('delete_at')}")

            movie = db['movies'].find_one({"file_id": file_id})
            if movie:
                movie_name = movie['name']
                movie_ops.append({"delete_one": {"filter": {"file_id": file_id}}})
                send_message(chat_id, f"Movie '{movie_name}' has been deleted as scheduled.")
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Deleted movie '{movie_name}' (file_id: {file_id}) for chat {chat_id}.")
            else:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] No movie found for file_id {file_id}, clearing deletion record.")

            deletion_ops.append({"delete_one": {"filter": {"_id": deletion_id}}})

        if movie_ops:
            try:
                db['movies'].bulk_write(movie_ops, ordered=False)
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Deleted {len(movie_ops)} movies.")
            except Exception as e:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Failed to delete movies: {str(e)}", critical=True)

        if deletion_ops:
            try:
                db['deletions'].bulk_write(deletion_ops, ordered=False)
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Cleared {len(deletion_ops)} deletion records via bulk write.")
            except Exception as e:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Bulk write failed: {str(e)}. Attempting individual deletes.", critical=True)
                for op in deletion_ops:
                    try:
                        db['deletions'].delete_one(op['delete_one']['filter'])
                        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Individually deleted deletion record with _id: {op['delete_one']['filter']['_id']}.")
                    except Exception as e:
                        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Failed to individually delete _id {op['delete_one']['filter']['_id']}: {str(e)}", critical=True)

        remaining = db['deletions'].count_documents({"delete_at": {"$lte": now}})
        if remaining > 0:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Warning: {remaining} deletion records remain after processing.", critical=True)

        if processed_count == 0:
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[process_scheduled_deletions] No deletions to process.")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Error: {str(e)}\n{traceback.format_exc()}", critical=True)