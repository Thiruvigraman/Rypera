from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient('your_mongo_uri_here')
db = client['movie_bot']
movies_collection = db['movies']
channels_collection = db['channels']

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
    # Logic to check if the bot is an admin in the channel
    return True  # This should be replaced with actual logic.