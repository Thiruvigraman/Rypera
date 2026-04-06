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

        # Indexes
        sent_files_collection.create_index([("chat_id", 1), ("file_message_id", 1)])
        users_collection.create_index([("user_id", 1)], unique=True)

        log_to_discord(
            "MongoDB connected successfully",
            "status",
            "info"
        )

        break

    except ConnectionFailure as e:
        if attempt == max_retries - 1:
            log_to_discord(
                "MongoDB connection failed",
                "status",
                "error",
                fields={"error": str(e)}
            )

            from bot import send_message
            send_message(ADMIN_ID, "❌ MongoDB connection failed. Bot is down.")

            raise

        time.sleep(10)


# ================= MOVIES =================
def load_movies():
    try:
        movies = {}
        for doc in movies_collection.find({}, {"name": 1, "file_id": 1, "_id": 0}):
            movies[doc['name']] = {"file_id": doc['file_id']}
        return movies

    except Exception as e:
        log_to_discord(
            "Error loading movies",
            "status",
            "error",
            fields={"error": str(e)}
        )
        raise


def save_movie(name, file_id):
    try:
        movies_collection.update_one(
            {"name": name},
            {
                "$set": {"file_id": file_id},
                "$setOnInsert": {"access_count": 0}  # 🔥 ensure field exists
            },
            upsert=True
        )

    except Exception as e:
        log_to_discord(
            "Error saving movie",
            "status",
            "error",
            fields={"movie": name, "error": str(e)}
        )
        raise


def delete_movie(name):
    try:
        movies_collection.delete_one({"name": name})

    except Exception as e:
        log_to_discord(
            "Error deleting movie",
            "status",
            "error",
            fields={"movie": name, "error": str(e)}
        )
        raise


def rename_movie(old_name, new_name):
    try:
        movie = movies_collection.find_one(
            {"name": old_name},
            {"file_id": 1, "access_count": 1, "_id": 0}
        )

        if movie:
            movies_collection.delete_one({"name": old_name})

            movies_collection.insert_one({
                "name": new_name,
                "file_id": movie["file_id"],
                "access_count": movie.get("access_count", 0)  # 🔥 preserve count
            })

            return True

        return False

    except Exception as e:
        log_to_discord(
            "Error renaming movie",
            "status",
            "error",
            fields={
                "old": old_name,
                "new": new_name,
                "error": str(e)
            }
        )
        raise


# 🔥 NEW: ACCESS TRACKING
def increment_movie_access(name):
    try:
        movies_collection.update_one(
            {"name": name},
            {"$inc": {"access_count": 1}},
            upsert=True
        )

    except Exception as e:
        log_to_discord(
            "Access count error",
            "status",
            "error",
            fields={"movie": name, "error": str(e)}
        )


def get_top_movies(limit=5):
    try:
        return list(
            movies_collection
            .find({}, {"name": 1, "access_count": 1, "_id": 0})
            .sort("access_count", -1)
            .limit(limit)
        )

    except Exception as e:
        log_to_discord(
            "Top movies fetch error",
            "status",
            "error",
            fields={"error": str(e)}
        )
        return []


# ================= USERS =================
def add_user(user_id, display_name):
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "display_name": display_name or "Unknown"
                }
            },
            upsert=True
        )

    except Exception as e:
        log_to_discord(
            "Error adding user",
            "status",
            "error",
            fields={"user_id": user_id, "error": str(e)}
        )
        raise


def get_all_users():
    try:
        return list(
            users_collection.find(
                {},
                {"user_id": 1, "display_name": 1, "_id": 0}
            )
        )

    except Exception as e:
        log_to_discord(
            "Error retrieving users",
            "status",
            "error",
            fields={"error": str(e)}
        )
        raise


def get_stats():
    try:
        movie_count = movies_collection.count_documents({})
        user_count = users_collection.count_documents({})

        return {
            "movie_count": movie_count,
            "user_count": user_count
        }

    except Exception as e:
        log_to_discord(
            "Error getting stats",
            "status",
            "error",
            fields={"error": str(e)}
        )
        raise


# ================= SENT FILES =================
def save_sent_file(chat_id, file_message_id, warning_message_id, timestamp):
    try:
        sent_files_collection.insert_one({
            "chat_id": chat_id,
            "file_message_id": file_message_id,
            "warning_message_id": warning_message_id,
            "timestamp": timestamp
        })

    except Exception as e:
        log_to_discord(
            "Error saving sent file",
            "status",
            "error",
            fields={"chat_id": chat_id, "error": str(e)}
        )
        raise


def get_pending_files(expiry_minutes=15):
    try:
        cutoff = time.time() - (expiry_minutes * 60)

        return list(
            sent_files_collection.find(
                {"timestamp": {"$gte": cutoff}}
            )
        )

    except Exception as e:
        log_to_discord(
            "Error getting pending files",
            "status",
            "error",
            fields={"error": str(e)}
        )
        raise


def delete_sent_file_record(chat_id, file_message_id):
    try:
        sent_files_collection.delete_one({
            "chat_id": chat_id,
            "file_message_id": file_message_id
        })

    except Exception as e:
        log_to_discord(
            "Error deleting sent file record",
            "status",
            "error",
            fields={"chat_id": chat_id, "error": str(e)}
        )
        raise