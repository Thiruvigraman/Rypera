# file: database.py

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import MONGODB_URI, ADMIN_ID
from webhook import log_to_discord
import time

# ================= MONGODB SETUP =================
max_retries = 5

for attempt in range(max_retries):
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
        client.server_info()

        db = client['telegram_bot']
        movies_collection = db['movies']
        users_collection = db['users']
        sent_files_collection = db['sent_files']

        sent_files_collection.create_index([("chat_id", 1), ("file_message_id", 1)])
        users_collection.create_index([("user_id", 1)], unique=True)

        log_to_discord("MongoDB connected successfully", "status", "info")
        break

    except ConnectionFailure as e:
        if attempt == max_retries - 1:
            log_to_discord("MongoDB connection failed", "status", "error")

            from bot import send_message
            send_message(ADMIN_ID, "❌ MongoDB failed")

            raise

        time.sleep(10)


# ================= MOVIES =================
def load_movies():
    movies = {}
    for doc in movies_collection.find({}, {"name": 1, "file_id": 1, "_id": 0}):
        movies[doc['name']] = {"file_id": doc['file_id']}
    return movies


def save_movie(name, file_id):
    movies_collection.update_one(
        {"name": name},
        {"$set": {"file_id": file_id}},
        upsert=True
    )


def delete_movie(name):
    movies_collection.delete_one({"name": name})


def rename_movie(old_name, new_name):
    movie = movies_collection.find_one({"name": old_name})
    if movie:
        save_movie(new_name, movie['file_id'])
        delete_movie(old_name)
        return True
    return False


# 🔥 NEW: ACCESS COUNT
def increment_movie_access(name):
    movies_collection.update_one(
        {"name": name},
        {"$inc": {"access_count": 1}},
        upsert=True
    )


def get_top_movies(limit=5):
    return list(
        movies_collection
        .find({}, {"name": 1, "access_count": 1, "_id": 0})
        .sort("access_count", -1)
        .limit(limit)
    )


# ================= USERS =================
def add_user(user_id, display_name):
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "display_name": display_name}},
        upsert=True
    )


def get_all_users():
    return list(users_collection.find({}, {"_id": 0}))


def get_stats():
    return {
        "movie_count": movies_collection.count_documents({}),
        "user_count": users_collection.count_documents({})
    }


# ================= SENT FILES =================
def save_sent_file(chat_id, file_message_id, warning_message_id, timestamp):
    sent_files_collection.insert_one({
        "chat_id": chat_id,
        "file_message_id": file_message_id,
        "warning_message_id": warning_message_id,
        "timestamp": timestamp
    })


def get_pending_files(expiry_minutes=15):
    cutoff = time.time() - (expiry_minutes * 60)
    return list(sent_files_collection.find({"timestamp": {"$gte": cutoff}}))


def delete_sent_file_record(chat_id, file_message_id):
    sent_files_collection.delete_one({
        "chat_id": chat_id,
        "file_message_id": file_message_id
    })