#database.py

import os
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
from utils import log_to_discord, DISCORD_WEBHOOK_STATUS, DISCORD_WEBHOOK_FILE_ACCESS

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "file_sharing_bot"

try:
    client = MongoClient(MONGODB_URI, maxPoolSize=5)
    client.admin.command('ping')
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[database] MongoDB connection failed: {str(e)}", critical=True)
    raise

def get_movie_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Retrieve a movie by name with case-insensitive and flexible matching."""
    try:
        normalized_name = " ".join(name.split())
        movie = client[DATABASE_NAME]["movies"].find_one({
            "name": {"$regex": f"^{normalized_name}$", "$options": "i"}
        })
        if movie:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie_by_name] Found movie '{movie['name']}' for input '{name}'")
        else:
            all_movies = client[DATABASE_NAME]["movies"].find({}, {"name": 1})
            movie_names = [m["name"] for m in all_movies]
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie_by_name] Movie '{name}' not found. Available: {', '.join(movie_names)}")
        return movie
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie_by_name] Error: {str(e)}", critical=True)
        return None

def get_all_movies() -> List[Dict[str, Any]]:
    """Retrieve all movies from the database."""
    try:
        movies = list(client[DATABASE_NAME]["movies"].find())
        return movies
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_all_movies] Error: {str(e)}", critical=True)
        return []

def update_movie_name(old_name: str, new_name: str) -> bool:
    """Update a movie's name."""
    try:
        result = client[DATABASE_NAME]["movies"].update_one(
            {"name": {"$regex": f"^{old_name}$", "$options": "i"}},
            {"$set": {"name": new_name}}
        )
        if result.modified_count > 0:
            client[DATABASE_NAME]["deletions"].update_one(
                {"name": {"$regex": f"^{old_name}$", "$options": "i"}},
                {"$set": {"name": new_name}}
            )
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[update_movie_name] Updated '{old_name}' to '{new_name}'")
            return True
        return False
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[update_movie_name] Error: {str(e)}", critical=True)
        return False

def delete_movie(name: str) -> bool:
    """Delete a movie and its deletion schedule."""
    try:
        movie = client[DATABASE_NAME]["movies"].find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if movie:
            client[DATABASE_NAME]["movies"].delete_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
            client[DATABASE_NAME]["deletions"].delete_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_movie] Deleted movie '{name}'")
            return True
        return False
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_movie] Error: {str(e)}", critical=True)
        return False

def schedule_message_deletion(chat_id: int, message_id: int, movie_name: str) -> None:
    """Schedule a message for deletion in a user's chat."""
    try:
        deletion_time = datetime.now(pytz.UTC) + timedelta(minutes=30)
        client[DATABASE_NAME]["message_deletions"].insert_one({
            "chat_id": chat_id,
            "message_id": message_id,
            "movie_name": movie_name,
            "delete_at": deletion_time
        })
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[schedule_message_deletion] Scheduled deletion for message {message_id} in chat {chat_id} for '{movie_name}'")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[schedule_message_deletion] Error: {str(e)}", critical=True)

def process_scheduled_message_deletions() -> int:
    """Process messages scheduled for deletion."""
    try:
        now = datetime.now(pytz.UTC)
        deletions = client[DATABASE_NAME]["message_deletions"].find({"delete_at": {"$lte": now}})
        deleted_count = 0
        for deletion in deletions:
            try:
                delete_message(deletion["chat_id"], deletion["message_id"])
                client[DATABASE_NAME]["message_deletions"].delete_one({"_id": deletion["_id"]})
                deleted_count += 1
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_message_deletions] Deleted message {deletion['message_id']} in chat {deletion['chat_id']} for '{deletion['movie_name']}'")
            except Exception as e:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_message_deletions] Failed to delete message {deletion['message_id']} in chat {deletion['chat_id']}: {str(e)}", critical=True)
        if deleted_count == 0:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_message_deletions] No message deletions to process.")
        return deleted_count
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_message_deletions] Error: {str(e)}", critical=True)
        return 0

def process_scheduled_deletions() -> tuple[int, int]:
    """Process movies scheduled for deletion."""
    try:
        now = datetime.now(pytz.UTC)
        deletions = client[DATABASE_NAME]["deletions"].find({"delete_at": {"$lte": now}})
        deleted_count = 0
        for deletion in deletions:
            client[DATABASE_NAME]["movies"].delete_one({"file_id": deletion["file_id"]})
            client[DATABASE_NAME]["deletions"].delete_one({"_id": deletion["_id"]})
            deleted_count += 1
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Deleted movie '{deletion['name']}'")
        
        remaining_count = client[DATABASE_NAME]["deletions"].count_documents({})
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Successfully fetched deletions")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Counted {remaining_count} remaining deletions")
        if deleted_count == 0:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] No deletions to process.")
        return deleted_count, remaining_count
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_scheduled_deletions] Error: {str(e)}", critical=True)
        return 0, 0

def cleanup_overdue_deletions() -> None:
    """Clean up overdue deletion records at startup."""
    try:
        now = datetime.now(pytz.UTC)
        result = client[DATABASE_NAME]["deletions"].delete_many({"delete_at": {"$lte": now}})
        if result.deleted_count > 0:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[cleanup_overdue_deletions] Removed {result.deleted_count} overdue deletion records")
        else:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[cleanup_overdue_deletions] No overdue deletion records found.")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[cleanup_overdue_deletions] Error: {str(e)}", critical=True)

def track_user(user: Dict[str, Any]) -> None:
    """Track user information."""
    try:
        user_id = user.get('id')
        username = f"@{user.get('username', 'unknown')}"
        client[DATABASE_NAME]["users"].update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "username": username,
                    "last_seen": datetime.now(pytz.UTC)
                }
            },
            upsert=True
        )
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[track_user] Updated user {user_id} ({username})")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[track_user] Error: {str(e)}", critical=True)

def get_all_users() -> List[Dict[str, Any]]:
    """Retrieve all users from the database."""
    try:
        users = list(client[DATABASE_NAME]["users"].find())
        return users
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_all_users] Error: {str(e)}", critical=True)
        return []

def close_connection() -> None:
    """Close MongoDB connection."""
    try:
        client.close()
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[close_db] MongoDB connection closed.")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[close_db] Error closing connection: {str(e)}", critical=True)