# file: database.py

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import MONGODB_URI, ADMIN_ID
from webhook import log_to_discord
import time
import secrets
import string

# ================= TOKEN =================
def generate_token(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


# ================= MONGODB SETUP =================
MONGO_AVAILABLE = True
max_retries = 5

for attempt in range(max_retries):
    try:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )

        client.server_info()

        db = client['telegram_bot']
        movies_collection = db['movies']
        users_collection = db['users']
        sent_files_collection = db['sent_files']

        # indexes
        sent_files_collection.create_index([("chat_id", 1), ("file_message_id", 1)])
        users_collection.create_index([("user_id", 1)], unique=True)
        movies_collection.create_index([("name", 1)], unique=True)
        movies_collection.create_index([("token", 1)], unique=True)

        log_to_discord("MongoDB connected", "status", "info")
        break

    except ConnectionFailure as e:
        MONGO_AVAILABLE = False

        if attempt == max_retries - 1:
            log_to_discord("MongoDB connection failed", "status", "error")

            try:
                from bot import send_message
                send_message(ADMIN_ID, "❌ MongoDB connection failed")
            except:
                pass

            raise

        time.sleep(5)


# ================= DB STATUS =================
def is_db_available():
    return MONGO_AVAILABLE


# ================= MOVIES =================
def load_movies():
    if not MONGO_AVAILABLE:
        return {}

    try:
        return {
            doc['name']: {
                "file_id": doc['file_id'],
                "token": doc.get("token")
            }
            for doc in movies_collection.find(
                {}, {"name": 1, "file_id": 1, "token": 1, "_id": 0}
            )
        }
    except Exception as e:
        log_to_discord("Load movies failed", "status", "error", fields={"error": str(e)})
        return {}


def save_movie(name, file_id):
    if not name or not file_id:
        return None

    try:
        # prevent duplicate token collision
        token = generate_token()

        movies_collection.update_one(
            {"name": name},
            {
                "$set": {
                    "file_id": file_id,
                    "token": token
                },
                "$setOnInsert": {"access_count": 0}
            },
            upsert=True
        )

        return token

    except Exception as e:
        log_to_discord(
            "Save movie failed",
            "status",
            "error",
            fields={"movie": name, "error": str(e)}
        )
        return None


def get_movie_by_token(token):
    if not token:
        return None

    try:
        return movies_collection.find_one({"token": token})
    except Exception as e:
        log_to_discord("Token lookup failed", "status", "error")
        return None


def delete_movie(name):
    try:
        movies_collection.delete_one({"name": name})
    except Exception as e:
        log_to_discord("Delete movie failed", "status", "error")


def rename_movie(old_name, new_name):
    try:
        movie = movies_collection.find_one({"name": old_name})

        if not movie:
            return False

        movies_collection.delete_one({"name": old_name})

        movies_collection.insert_one({
            "name": new_name,
            "file_id": movie["file_id"],
            "token": movie.get("token"),
            "access_count": movie.get("access_count", 0)
        })

        return True

    except Exception as e:
        log_to_discord("Rename failed", "status", "error", fields={"error": str(e)})
        return False


# ================= ACCESS =================
def increment_movie_access(name):
    try:
        movies_collection.update_one(
            {"name": name},
            {"$inc": {"access_count": 1}},
            upsert=True
        )
    except Exception as e:
        log_to_discord("Access increment failed", "status", "error")


def get_top_movies(limit=5):
    try:
        return list(
            movies_collection
            .find({}, {"name": 1, "access_count": 1, "_id": 0})
            .sort("access_count", -1)
            .limit(limit)
        )
    except Exception as e:
        log_to_discord("Top movies failed", "status", "error")
        return []


# ================= USERS =================
def add_user(user_id, display_name):
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "display_name": display_name}},
            upsert=True
        )
    except Exception as e:
        log_to_discord("Add user failed", "status", "error")


def get_all_users():
    try:
        return list(users_collection.find({}, {"user_id": 1, "_id": 0}))
    except Exception as e:
        log_to_discord("Get users failed", "status", "error")
        return []


def get_stats():
    try:
        return {
            "movie_count": movies_collection.count_documents({}),
            "user_count": users_collection.count_documents({})
        }
    except Exception as e:
        log_to_discord("Stats failed", "status", "error")
        return {"movie_count": 0, "user_count": 0}


# ================= FILE CLEAN =================
def save_sent_file(chat_id, file_message_id, warning_message_id, timestamp):
    try:
        sent_files_collection.insert_one({
            "chat_id": chat_id,
            "file_message_id": file_message_id,
            "warning_message_id": warning_message_id,
            "timestamp": timestamp
        })
    except Exception as e:
        log_to_discord("Save sent file failed", "status", "error")


def get_pending_files(expiry_minutes=15):
    try:
        cutoff = time.time() - (expiry_minutes * 60)
        return list(sent_files_collection.find({"timestamp": {"$gte": cutoff}}))
    except Exception as e:
        log_to_discord("Get pending failed", "status", "error")
        return []


def delete_sent_file_record(chat_id, file_message_id):
    try:
        sent_files_collection.delete_one({
            "chat_id": chat_id,
            "file_message_id": file_message_id
        })
    except Exception as e:
        log_to_discord("Delete record failed", "status", "error")


# ================= DB SIZE =================
def get_db_size_mb():
    try:
        stats = db.command("dbStats")
        size_bytes = stats.get("dataSize", 0)
        size_mb = size_bytes / 1024 / 1024
        return round(size_mb, 2)
    except Exception as e:
        log_to_discord(
            "DB size fetch failed",
            "status",
            "error",
            fields={"error": str(e)}
        )
        return 0