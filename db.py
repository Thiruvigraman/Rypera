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

def load_movies() -> list:
    """
    Load movies from the database.
    
    Returns:
    list: A list of movies.
    """
    try:
        movies = list(movies_collection.find())
        return movies
    except Exception as e:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"⚠️ Failed to load movies: {e} 🔴")
        return []

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

def delete_movie(user_id: int, name: str) -> None:
    """
    Delete a movie from the database.
    
    Args:
    user_id (int): The user ID.
    name (str): The movie name.
    """
    if not is_admin(user_id):
        raise PermissionError("🔒 You are not authorized to delete a movie. 🚫")

    try:
        result = movies_collection.delete_one({'name': name})
        if result.deleted_count > 0:
            log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"🗑️ Admin deleted movie: {name} 🔴")
        else:
            log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"⚠️ Movie '{name}' not found for deletion.")
    except Exception as e:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"⚠️ Error deleting movie '{name}': {e} 🔴")
        raise Exception(f"⚠️ Error deleting movie: {e}")

def rename_movie(user_id: int, old_name: str, new_name: str) -> bool:
    """
    Rename a movie in the database.
    
    Args:
    user_id (int): The user ID.
    old_name (str): The old movie name.
    new_name (str): The new movie name.
    
    Returns:
    bool: True if the movie was renamed, False otherwise.
    """
    if not is_admin(user_id):
        raise PermissionError("🔒 You are not authorized to rename a movie. 🚫")

    try:
        result = movies_collection.update_one({'name': old_name}, {'$set': {'name': new_name}})
        if result.modified_count > 0:
            log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"📝 Admin renamed movie: {old_name} to {new_name} ✨")
            return True
        return False
    except Exception as e:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"⚠️ Error renaming movie '{old_name}' to '{new_name}': {e} 🔴")
        raise Exception(f"⚠️ Error renaming movie: {e}")