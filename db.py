import os
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from discord_webhook import log_to_discord

# Load environment variables
load_dotenv()

# Get Mongo URI and Admin ID from .env or Render environment settings
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
    # Log successful connection to Discord
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), "Successfully connected to MongoDB.")
except Exception as e:
    # Log the connection error to Discord
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Error connecting to MongoDB: {e}")
    raise Exception(f"Error connecting to MongoDB: {e}")

# Helper function to check if user is admin
def is_admin(user_id):
    return str(user_id) == ADMIN_ID

# Load movies from the database
def load_movies():
    return {movie['name']: movie for movie in movies_collection.find()}

# Save a new movie to the database (only admin can use this)
def save_movie(user_id, name: str, file_id: str):
    if not is_admin(user_id):
        raise PermissionError("You are not authorized to add a movie.")
    
    movie = {
        'name': name,
        'file_id': file_id
    }
    movies_collection.insert_one(movie)
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Admin added a new movie: {name} with file_id: {file_id}")

# Delete a movie from the database (only admin can use this)
def delete_movie(user_id, name: str):
    if not is_admin(user_id):
        raise PermissionError("You are not authorized to delete a movie.")
    
    movies_collection.delete_one({'name': name})
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Admin deleted movie: {name}")

# Rename a movie in the database (only admin can use this)
def rename_movie(user_id, old_name: str, new_name: str):
    if not is_admin(user_id):
        raise PermissionError("You are not authorized to rename a movie.")
    
    result = movies_collection.update_one({'name': old_name}, {'$set': {'name': new_name}})
    if result.modified_count > 0:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Admin renamed movie: {old_name} to {new_name}")
        return True
    return False

# Register a new channel (only admin can use this)
def register_channel(user_id, channel_id: str, channel_name: str):
    if not is_admin(user_id):
        raise PermissionError("You are not authorized to register a channel.")
    
    channels_collection.insert_one({
        'channel_id': channel_id,
        'channel_name': channel_name
    })
    log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"Admin registered new channel: {channel_name}")

# Check if a user is an admin in a channel (this can be extended based on actual implementation)
def check_if_admin(channel_id: str):
    # You may implement this based on actual channel admin check logic
    return True