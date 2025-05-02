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

def save_movie(file_id: str, name: str, chat_id: int) -> None:
    """Save a movie to the database with deletion scheduling."""
    try:
        deletion_minutes = int(os.getenv("DELETION_MINUTES", 30))
        deletion_time = datetime.now(pytz.UTC) + timedelta(minutes=deletion_minutes)
        
        client[DATABASE_NAME]["movies"].insert_one({
            "file_id": file_id,
            "name": name,
            "chat_id": chat_id,
            "created_at": datetime.now(pytz.UTC)
        })
        
        client[DATABASE_NAME]["deletions"].insert_one({
            "file_id": file_id,
            "name": name,
            "chat_id": chat_id,
            "delete_at": deletion_time
        })
        
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[save_movie] Saved movie '{name}' with file_id {file_id} for chat {chat_id}")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[save_movie] Error: {str(e)}", critical=True)

def get_movie_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Retrieve a movie by name with case-insensitive and flexible matching."""
    try:
        # Normalize input: collapse multiple spaces, strip
        normalized_name = " ".join(name.split())
        # Use regex for case-insensitive partial match
        movie = client[DATABASE_NAME]["movies"].find_one({
            "name": {"$regex": f"^{normalized_name}$", "$options": "i"}
        })
        if movie:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie_by_name] Found movie '{movie['name']}' for input '{name}'")
        else:
            # Log all movie names for debugging
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
            {"name": old_name},
            {"$set": {"name": new_name}}
        )
        if result.modified_count > 0:
            client[DATABASE_NAME]["deletions"].update_one(
                {"name": old_name},
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
        movie = client[DATABASE_NAME]["movies"].find_one({"name": name})
        if movie:
            client[DATABASE_NAME]["movies"].delete_one({"name": name})
            client[DATABASE_NAME]["deletions"].delete_one({"name": name})
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_movie] Deleted movie '{name}'")
            return True
        return False
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_movie] Error: {str(e)}", critical=True)
        return False

def save_temp_file_id(chat_id: int, file_id: str) -> None:
    """Save a temporary file ID."""
    try:
        client[DATABASE_NAME]["temp_files"].update_one(
            {"chat_id": chat_id},
            {"$set": {"file_id": file_id, "created_at": datetime.now(pytz.UTC)}},
            upsert=True
        )
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[save_temp_file_id] Saved temp file_id {file_id} for chat {chat_id}")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[save_temp_file_id] Error: {str(e)}", critical=True)

def get_temp_file_id(chat_id: int) -> Optional[str]:
    """Retrieve a temporary file ID."""
    try:
        temp_file = client[DATABASE_NAME]["temp_files"].find_one({"chat_id": chat_id})
        return temp_file["file_id"] if temp_file else None
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_temp_file_id] Error: {str(e)}", critical=True)
        return None

def delete_temp_file_id(chat_id: int) -> None:
    """Delete a temporary file ID."""
    try:
        client[DATABASE_NAME]["temp_files"].delete_one({"chat_id": chat_id})
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[delete_temp_file_id] Deleted temp file for chat {chat_id}")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_temp_file_id] Error: {str(e)}", critical=True)

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