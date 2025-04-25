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

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client['movie_bot']
    movies_collection = db['movies']
    channels_collection = db['channels']
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), "✅ Successfully connected to MongoDB.")
except Exception as e:
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"❌ Error connecting to MongoDB: {e}")
    raise Exception(f"❌ Error connecting to MongoDB: {e}")

# Helper function to check if the user is an admin
def is_admin(user_id: int) -> bool:
    return str(user_id) == ADMIN_ID

# Load movies from the database
def load_movies() -> dict:
    return {movie['name']: movie for movie in movies_collection.find()}

# Save a new movie to the database
def save_movie(user_id: int, name: str, file_id: str):
    if not is_admin(user_id):
        raise PermissionError("❌ You are not authorized to add a movie.")
    movie = {'name': name, 'file_id': file_id}
    movies_collection.insert_one(movie)
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin added a new movie: {name} with file_id: {file_id}")

# Delete a movie from the database
def delete_movie(user_id: int, name: str):
    if not is_admin(user_id):
        raise PermissionError("❌ You are not authorized to delete a movie.")
    movies_collection.delete_one({'name': name})
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin deleted movie: {name}")

# Rename a movie in the database
def rename_movie(user_id: int, old_name: str, new_name: str) -> bool:
    if not is_admin(user_id):
        raise PermissionError("❌ You are not authorized to rename a movie.")
    result = movies_collection.update_one({'name': old_name}, {'$set': {'name': new_name}})
    if result.modified_count > 0:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin renamed movie: {old_name} to {new_name}")
        return True
    return False

# Save channel data to the database
def save_channel(user_id: int, channel_id: str):
    if not is_admin(user_id):
        raise PermissionError("❌ You are not authorized to save a channel.")
    channels_collection.update_one(
        {'channel_id': channel_id}, 
        {'$set': {'channel_id': channel_id}}, 
        upsert=True
    )
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"✅ Admin saved channel: {channel_id}")

# Load saved channels
def load_channels() -> dict:
    return {channel['channel_id']: channel for channel in channels_collection.find()}