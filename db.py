import os
from pymongo import MongoClient
from dotenv import load_dotenv
from discord_webhook import log_to_discord

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
ADMIN_ID = os.getenv('ADMIN_ID')

if not MONGO_URI:
    raise ValueError("MONGO_URI not set in environment variables.")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID not set in environment variables.")

try:
    client = MongoClient(MONGO_URI)
    db = client['movie_bot']
    movies_collection = db['movies']
    channels_collection = db['channels']
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), "✅ Successfully connected to MongoDB.")
except Exception as e:
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"❌ Error connecting to MongoDB: {e}")
    raise Exception(f"❌ Error connecting to MongoDB: {e}")

def is_admin(user_id: int) -> bool:
    return str(user_id) == ADMIN_ID

def load_movies() -> dict:
    return {movie['name']: movie for movie in movies_collection.find()}

def save_movie(user_id: int, name: str, file_id: str):
    if not is_admin(user_id):
        raise PermissionError("❌ You are not authorized to add a movie.")
    movie = {'name': name, 'file_id': file_id}
    movies_collection.insert_one(movie)
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin added a new movie: {name} with file_id: {file_id}")

def delete_movie(user_id: int, name: str):
    if not is_admin(user_id):
        raise PermissionError("❌ You are not authorized to delete a movie.")
    movies_collection.delete_one({'name': name})
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin deleted movie: {name}")

def rename_movie(user_id: int, old_name: str, new_name: str) -> bool:
    if not is_admin(user_id):
        raise PermissionError("❌ You are not authorized to rename a movie.")
    result = movies_collection.update_one({'name': old_name}, {'$set': {'name': new_name}})
    if result.modified_count > 0:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin renamed movie: {old_name} to {new_name}")
        return True
    return False