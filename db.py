import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['movie_bot_db']
movies_collection = db['movies']

def add_movie(movie_data):
    try:
        movies_collection.insert_one(movie_data)
        return True
    except Exception as e:
        print(f"Error adding movie: {e}")
        return False

def get_movie(title):
    try:
        return movies_collection.find_one({"title": title})
    except Exception as e:
        print(f"Error getting movie: {e}")
        return None

def update_movie(title, updated_data):
    try:
        result = movies_collection.update_one({"title": title}, {"$set": updated_data})
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating movie: {e}")
        return False

def delete_movie(title):
    try:
        result = movies_collection.delete_one({"title": title})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting movie: {e}")
        return False