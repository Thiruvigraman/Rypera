# database.py

from pymongo import MongoClient
from config import MONGODB_URI
import logging
import time

# Configure logging to Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
db = client['bot']
movies_collection = db['movies']
sent_files_collection = db['sent_files']
users_collection = db['users']

_movies_cache = None  # Cache for movie data

def load_movies():
    global _movies_cache
    if _movies_cache is None:
        logger.info("Loading movies from MongoDB into cache")
        _movies_cache = {}
        for doc in movies_collection.find():
            _movies_cache[doc['name']] = {"file_id": doc['file_id']}
        logger.info(f"Loaded {len(_movies_cache)} movies into cache")
    return _movies_cache

def save_movie(name, file_id):
    global _movies_cache
    movies_collection.insert_one({"name": name, "file_id": file_id})
    if _movies_cache is not None:
        _movies_cache[name] = {"file_id": file_id}
    logger.info(f"Saved movie '{name}' to MongoDB and cache")

def delete_movie(name):
    global _movies_cache
    result = movies_collection.delete_one({"name": name})
    if result.deleted_count and _movies_cache is not None:
        _movies_cache.pop(name, None)
    logger.info(f"Deleted movie '{name}' from MongoDB and cache")
    return result.deleted_count > 0

def rename_movie(old_name, new_name):
    global _movies_cache
    result = movies_collection.update_one({"name": old_name}, {"$set": {"name": new_name}})
    if result.modified_count and _movies_cache is not None:
        if old_name in _movies_cache:
            _movies_cache[new_name] = _movies_cache.pop(old_name)
    logger.info(f"Renamed movie '{old_name}' to '{new_name}' in MongoDB and cache")
    return result.modified_count > 0

def add_user(user_id, display_name):
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"display_name": display_name, "timestamp": time.time()}},
        upsert=True
    )

def get_all_users():
    return list(users_collection.find())

def get_stats():
    return {
        "movie_count": movies_collection.count_documents({}),
        "user_count": users_collection.count_documents({})
    }