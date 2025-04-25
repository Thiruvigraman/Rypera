import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to MongoDB
MONGO_URI = os.getenv('MONGO_URI')  # Replace with your actual MongoDB URI
client = MongoClient(MONGO_URI)
db = client['movie_bot_db']  # Database name

# You can add more collections as per your needs
movies_collection = db['movies']

# Function to insert a movie into the database
def add_movie(movie_data):
    try:
        movies_collection.insert_one(movie_data)
        return True
    except Exception as e:
        print(f"Error adding movie: {e}")
        return False

# Function to get a movie from the database by title
def get_movie(title):
    try:
        movie = movies_collection.find_one({"title": title})
        return movie
    except Exception as e:
        print(f"Error getting movie: {e}")
        return None

# Function to update a movie's information in the database
def update_movie(title, updated_data):
    try:
        result = movies_collection.update_one({"title": title}, {"$set": updated_data})
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating movie: {e}")
        return False

# Function to delete a movie from the database
def delete_movie(title):
    try:
        result = movies_collection.delete_one({"title": title})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting movie: {e}")
        return False