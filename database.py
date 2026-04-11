# file: database.py

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from config import MONGODB_URI, ADMIN_ID
from webhook import log_to_discord
import time
import secrets
import string


# ================= TOKEN =================
def generate_token(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_unique_token():
    # 🔥 guarantee uniqueness
    for _ in range(5):
        token = generate_token()
        if not movies_collection.find_one({"token": token}):
            return token
    return generate_token()


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
        movies_collection.create_index(
    [("token", 1)],
    unique=True,
    partialFilterExpression={"token": {"$exists": True, "$ne": None}}
)

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
        log_to_discord("Load movies failed", "status", "error")
        return {}


def save_movie(name, file_id):
    if not name or not file_id or not MONGO_AVAILABLE:
        return None

    try:
        token = generate_unique_token()

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

    except DuplicateKeyError:
        return save_movie(name, file_id)

    except Exception as e:
        log_to_discord("Save movie failed", "status", "error")
        return None


def get_movie_by_token(token):
    if not token or not MONGO_AVAILABLE:
        return None

    try:
        return movies_collection.find_one({"token": token})
    except:
        return None


def delete_movie(name):
    if not MONGO_AVAILABLE:
        return

    try:
        movies_collection.delete_one({"name": name})
    except:
        pass


def rename_movie(old_name, new_name):
    if not MONGO_AVAILABLE:
        return False

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

    except:
        return False


# ================= ACCESS =================
def increment_movie_access(name):
    if not MONGO_AVAILABLE:
        return

    try:
        movies_collection.update_one(
            {"name": name},
            {"$inc": {"access_count": 1}},
            upsert=True
        )
    except:
        pass


def get_top_movies(limit=5):
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(
            movies_collection
            .find({}, {"name": 1, "access_count": 1, "_id": 0})
            .sort("access_count", -1)
            .limit(limit)
        )
    except:
        return []


# ================= USERS =================
def add_user(user_id, display_name):
    if not MONGO_AVAILABLE:
        return

    try:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "display_name": display_name}},
            upsert=True
        )
    except:
        pass


def get_all_users():
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(users_collection.find({}, {"user_id": 1, "_id": 0}))
    except:
        return []


def get_stats():
    if not MONGO_AVAILABLE:
        return {"movie_count": 0, "user_count": 0}

    try:
        return {
            "movie_count": movies_collection.count_documents({}),
            "user_count": users_collection.count_documents({})
        }
    except:
        return {"movie_count": 0, "user_count": 0}


# ================= FILE CLEAN =================
def save_sent_file(chat_id, file_message_id, warning_message_id, timestamp):
    if not MONGO_AVAILABLE:
        return

    try:
        sent_files_collection.insert_one({
            "chat_id": chat_id,
            "file_message_id": file_message_id,
            "warning_message_id": warning_message_id,
            "timestamp": timestamp
        })
    except:
        pass


def get_pending_files(expiry_minutes=15):
    if not MONGO_AVAILABLE:
        return []

    try:
        cutoff = time.time() - (expiry_minutes * 60)
        return list(sent_files_collection.find({"timestamp": {"$gte": cutoff}}))
    except:
        return []


def delete_sent_file_record(chat_id, file_message_id):
    if not MONGO_AVAILABLE:
        return

    try:
        sent_files_collection.delete_one({
            "chat_id": chat_id,
            "file_message_id": file_message_id
        })
    except:
        pass


# ================= DB SIZE =================
def get_db_size_mb():
    if not MONGO_AVAILABLE:
        return 0

    try:
        stats = db.command("dbStats")
        size_bytes = stats.get("dataSize", 0)
        size_mb = size_bytes / 1024 / 1024
        return round(size_mb, 2)
    except:
        return 0