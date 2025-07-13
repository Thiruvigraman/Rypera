# database.py
from pymongo import MongoClient
from config import MONGODB_URI, DISCORD_WEBHOOK_STATUS
from discord import log_to_discord

# MongoDB Setup
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Force connection to test
    db = client['telegram_bot']
    movies_collection = db['movies']
    users_collection = db['users']  # New collection for users
    log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.")
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ Failed to connect to MongoDB: {e}")
    raise e

def load_movies():
    movies = {}
    for doc in movies_collection.find():
        movies[doc['name']] = {"file_id": doc['file_id']}
    return movies

def save_movie(name, file_id):
    movies_collection.update_one({"name": name}, {"$set": {"file_id": file_id}}, upsert=True)

def delete_movie(name):
    movies_collection.delete_one({"name": name})

def rename_movie(old_name, new_name):
    movie = movies_collection.find_one({"name": old_name})
    if movie:
        delete_movie(old_name)
        save_movie(new_name, movie['file_id'])
        return True
    return False

def add_user(user_id):
    """Add a user ID to the users collection if not already present."""
    users_collection.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

def get_all_users():
    """Retrieve all user IDs from the users collection."""
    return [doc['user_id'] for doc in users_collection.find()]

def get_stats():
    """Retrieve statistics: total movies and unique users."""
    movie_count = movies_collection.count_documents({})
    user_count = users_collection.count_documents({})
    return {"movie_count": movie_count, "user_count": user_count}