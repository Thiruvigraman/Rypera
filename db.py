import os
from pymongo import MongoClient
from dotenv import load_dotenv
from discord_webhook import log_to_discord

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
ADMIN_ID = os.getenv('ADMIN_ID')

if not MONGO_URI:
    raise ValueError("MONGO_URI not set in environment variables. ❌")

if not ADMIN_ID:
    raise ValueError("ADMIN_ID not set in environment variables. ❌")

try:
    # Connecting to MongoDB
    client = MongoClient(MONGO_URI)
    db = client['movie_bot']
    movies_collection = db['movies']
    channels_collection = db['channels']

    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), "🔗 Successfully connected to MongoDB. ✅")
except Exception as e:
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"⚠️ Error connecting to MongoDB: {e} 🔴")
    raise Exception(f"⚠️ Error connecting to MongoDB: {e}")

def is_admin(user_id: int) -> bool:
    """
    Check if a user is an admin.
    
    Args:
    user_id (int): The user ID to check.
    
    Returns:
    bool: True if the user is an admin, False otherwise.
    """
    return str(user_id) == ADMIN_ID

def save_movie(user_id: int, name: str, file_id: str) -> None:
    """
    Save a new movie to the database.
    
    Args:
    user_id (int): The user ID.
    name (str): The movie name.
    file_id (str): The movie file ID.
    """
    if not is_admin(user_id):
        raise PermissionError("🔒 You are not authorized to add a movie. 🚫")

    try:
        movie = {'name': name, 'file_id': file_id}
        movies_collection.insert_one(movie)

        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"🎥 Admin added a new movie: {name} with file_id: {file_id} 📎")
    except Exception as e:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"⚠️ Error saving movie '{name}': {e} 🔴")
        raise Exception(f"⚠️ Error saving movie: {e}")