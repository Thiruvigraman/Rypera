import os
from pymongo import MongoClient
from dotenv import load_dotenv
from discord_webhook import log_to_discord

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
ADMIN_ID = os.getenv('ADMIN_ID')

if not MONGO_URI:
    raise ValueError("MONGO_URI not set in environment variables.")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID not set in environment variables.")

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client['movie_bot']
    movies_collection = db['movies']
    channels_collection = db['channels']
    
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), "Successfully connected to MongoDB.")
except Exception as e:
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Error connecting to MongoDB: {e}")
    raise Exception(f"Error connecting to MongoDB: {e}")

# Helper function to check if the user is an admin
def is_admin(user_id: int) -> bool:
    """
    Check if a user is an admin.
    
    Args:
    user_id (int): The user ID to check.
    
    Returns:
    bool: True if the user is an admin, False otherwise.
    """
    return str(user_id) == ADMIN_ID

# Load movies from the database
def load_movies() -> dict:
    """
    Load movies from the database.
    
    Returns:
    dict: A dictionary of movies.
    """
    return {movie['name']: movie for movie in movies_collection.find()}

# Save a new movie to the database
def save_movie(user_id: int, name: str, file_id: str) -> None:
    """
    Save a new movie to the database.
    
    Args:
    user_id (int): The user ID.
    name (str): The movie name.
    file_id (str): The movie file ID.
    """
    if not is_admin(user_id):
        raise PermissionError("You are not authorized to add a movie.")
    
    movie = {'name': name, 'file_id': file_id}
    movies_collection.insert_one(movie)
    
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Admin added a new movie: {name} with file_id: {file_id}")

# Delete a movie from the database
def delete_movie(user_id: int, name: str) -> None:
    """
    Delete a movie from the database.
    
    Args:
    user_id (int): The user ID.
    name (str): The movie name.
    """
    if not is_admin(user_id):
        raise PermissionError("You are not authorized to delete a movie.")
    
    movies_collection.delete_one({'name': name})
    
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Admin deleted movie: {name}")

# Rename a movie in the database
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
        raise PermissionError("You are not authorized to rename a movie.")
    
    result = movies_collection.update_one({'name': old_name}, {'$set': {'name': new_name}})
    
    if result.modified_count > 0:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Admin renamed movie: {old_name} to {new_name}")
        return True
    return False

# Save channel data to the database
def save_channel(user_id: int, channel_id: str) -> None:
    """
    Save a channel to the database.
    
    Args:
    user_id (int): The user ID.
    channel_id (str): The channel ID.
    """
    if not is_admin(user_id):
        raise PermissionError("You are not authorized to add a channel.")
    
    channel = {'channel_id': channel_id}
    channels_collection.insert_one(channel)
    
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Admin added a new channel: {channel_id}")