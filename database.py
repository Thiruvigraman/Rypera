#database.py
from pymongo import MongoClient
from config import MONGODB_URI, DISCORD_WEBHOOK_STATUS
from utils import log_to_discord

client = None
db = None
movies_collection = None

def connect_db():
    global client, db, movies_collection
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client['telegram_bot']
        movies_collection = db['movies']
        log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ Failed to connect to MongoDB: {e}")
        raise e

def close_db():
    if client:
        client.close()

def load_movies():
    return {doc['name']: {"file_id": doc['file_id']} for doc in movies_collection.find()}

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