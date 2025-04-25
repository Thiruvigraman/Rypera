import os
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from discord_webhook import log_to_discord

# Load environment variables
load_dotenv()

# Get Mongo URI from .env or Render environment settings
MONGO_URI = os.getenv('MONGO_URI')
if not MONGO_URI:
    raise ValueError("MONGO_URI not set in environment variables.")

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

def load_movies():
    return {movie['name']: movie for movie in movies_collection.find()}

def save_movie(name: str, file_id: str):
    movie = {
        'name': name,
        'file_id': file_id
    }
    movies_collection.insert_one(movie)

def delete_movie(name: str):
    movies_collection.delete_one({'name': name})

def rename_movie(old_name: str, new_name: str):
    result = movies_collection.update_one({'name': old_name}, {'$set': {'name': new_name}})
    return result.modified_count > 0

def register_channel(channel_id: str, channel_name: str):
    channels_collection.insert_one({
        'channel_id': channel_id,
        'channel_name': channel_name
    })

def check_if_admin(channel_id: str):
    # Replace this with real check if needed
    return True