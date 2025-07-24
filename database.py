"database.py 

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import MONGODB_URI, DISCORD_WEBHOOK_STATUS
from webhook import log_to_discord
import time

# MongoDB Setup with retry
max_retries = 3
for attempt in range(max_retries):
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  # Force connection to test
        db = client['telegram_bot']
        movies_collection = db['movies']
        users_collection = db['users']
        sent_files_collection = db['sent_files']
        sent_files_collection.create_index([("chat_id", 1), ("file_message_id", 1)])
        users_collection.create_index([("user_id", 1)], unique=True)
        log_to_discord(DISCORD_WEBHOOK_STATUS, "MongoDB connected successfully.", log_type='status')
        break
    except ConnectionFailure as e:
        if attempt < max_retries - 1:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"MongoDB connection attempt {attempt + 1} failed: {e}, retrying...", log_type='status')
            time.sleep(5)
        else:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Failed to connect to MongoDB after {max_retries} attempts: {e}", log_type='status')
            raise

def load_movies():
    try:
        movies = {}
        for doc in movies_collection.find({}, {"name": 1, "file_id": 1, "_id": 0}):
            movies[doc['name']] = {"file_id": doc['file_id']}
        return movies
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error loading movies: {e}", log_type='status')
        raise

def save_movie(name, file_id):
    try:
        movies_collection.update_one({"name": name}, {"$set": {"file_id": file_id}}, upsert=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error saving movie {name}: {e}", log_type='status')
        raise

def delete_movie(name):
    try:
        movies_collection.delete_one({"name": name})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error deleting movie {name}: {e}", log_type='status')
        raise

def rename_movie(old_name, new_name):
    try:
        movie = movies_collection.find_one({"name": old_name}, {"file_id": 1, "_id": 0})
        if movie:
            delete_movie(old_name)
            save_movie(new_name, movie['file_id'])
            return True
        return False
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error renaming movie {old_name} to {new_name}: {e}", log_type='status')
        raise

def add_user(user_id, display_name):
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "display_name": display_name or "Unknown"}},
            upsert=True
        )
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error adding user {user_id}: {e}", log_type='status')
        raise

def get_all_users():
    try:
        return list(users_collection.find({}, {"user_id": 1, "display_name": 1, "_id": 0}))
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error retrieving users: {e}", log_type='status')
        raise

def get_stats():
    try:
        movie_count = movies_collection.count_documents({})
        user_count = users_collection.count_documents({})
        return {"movie_count": movie_count, "user_count": user_count}
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error getting stats: {e}", log_type='status')
        raise

def save_sent_file(chat_id, file_message_id, warning_message_id, timestamp):
    try:
        sent_files_collection.insert_one({
            "chat_id": chat_id,
            "file_message_id": file_message_id,
            "warning_message_id": warning_message_id,
            "timestamp": timestamp
        })
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error saving sent file for chat {chat_id}: {e}", log_type='status')
        raise

def get_pending_files(expiry_minutes=15):
    try:
        cutoff = time.time() - (expiry_minutes * 60)
        return list(sent_files_collection.find({"timestamp": {"$gte": cutoff}}))
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error getting pending files: {e}", log_type='status')
        raise

def delete_sent_file_record(chat_id, file_message_id):
    try:
        sent_files_collection.delete_one({"chat_id": chat_id, "file_message_id": file_message_id})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error deleting sent file record for chat {chat_id}: {e}", log_type='status')
        raise