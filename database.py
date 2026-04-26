# file: database.py

import time
import secrets
import string
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from config import MONGODB_URI, ADMIN_ID
from webhook import log_to_discord
from redis_client import get_cache, set_cache, delete_cache, REDIS_AVAILABLE



# ================= TOKEN =================
def generate_token(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_unique_token():
    for _ in range(10):  # limit attempts
        token = generate_token()
        if not movies_collection.find_one({"token": token}):
            return token

    return generate_token()  # fallback


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
        sent_files_collection.create_index(
            [("chat_id", 1), ("file_message_id", 1)]
        )

        users_collection.create_index(
            [("user_id", 1)],
            unique=True
        )

        movies_collection.create_index(
            [("name", 1)],
            unique=True
        )

        # safe token index
        existing_indexes = movies_collection.index_information()

        if "token_1" not in existing_indexes:
            movies_collection.create_index(
                [("token", 1)],
                unique=True,
                name="token_1"
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
            except Exception:
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



# save_movie
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

        if REDIS_AVAILABLE:
            set_cache(f"movie:{name}", {"file_id": file_id, "token": token}, ttl=3600)
            set_cache(f"token:{token}", name, ttl=3600)

        return token

    except Exception:
        log_to_discord("Save movie failed", "status", "error")
        return None


# get_movie_by_token (🔥 HUGE SPEED BOOST)
def get_movie_by_token(token):
    if not token:
        return None

    if REDIS_AVAILABLE:
        name = get_cache(f"token:{token}")
        if name:
            movie = get_cache(f"movie:{name}")
            if movie:
                return {"name": name, **movie}

    if not MONGO_AVAILABLE:
        return None

    try:
        movie = movies_collection.find_one({"token": token})

        if movie and REDIS_AVAILABLE:
            name = movie["name"]
            set_cache(f"movie:{name}", {
                "file_id": movie["file_id"],
                "token": movie["token"]
            }, ttl=3600)
            set_cache(f"token:{token}", name, ttl=3600)

        return movie

    except Exception:
        return None


# delete_movie
def delete_movie(name):
    if not MONGO_AVAILABLE:
        return

    try:
        movie = movies_collection.find_one({"name": name})
        movies_collection.delete_one({"name": name})

        if REDIS_AVAILABLE and movie:
            delete_cache(f"movie:{name}")
            delete_cache(f"token:{movie.get('token')}")

    except Exception:
        pass

# rename_movie
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

        if REDIS_AVAILABLE:
            delete_cache(f"movie:{old_name}")
            set_cache(f"movie:{new_name}", {
                "file_id": movie["file_id"],
                "token": movie.get("token")
            }, ttl=3600)

        return True

    except Exception:
        return False

def load_movies_cached():
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
    except Exception:
        return {}


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
    except Exception:
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
    except Exception:
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
    except Exception:
        pass


def get_all_users():
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(users_collection.find({}, {"user_id": 1, "_id": 0}))
    except Exception:
        return []


def get_stats():
    if not MONGO_AVAILABLE:
        return {"movie_count": 0, "user_count": 0}

    try:
        return {
            "movie_count": movies_collection.count_documents({}),
            "user_count": users_collection.count_documents({})
        }
    except Exception:
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
    except Exception:
        pass


def get_pending_files(expiry_minutes=15):
    if not MONGO_AVAILABLE:
        return []

    try:
        cutoff = time.time() - (expiry_minutes * 60)
        return list(sent_files_collection.find({"timestamp": {"$gte": cutoff}}))
    except Exception:
        return []


def delete_sent_file_record(chat_id, file_message_id):
    if not MONGO_AVAILABLE:
        return

    try:
        sent_files_collection.delete_one({
            "chat_id": chat_id,
            "file_message_id": file_message_id
        })
    except Exception:
        pass



# ================= LOG STORAGE =================

def save_access_log(user_id, movie_name):
    if not MONGO_AVAILABLE:
        return

    try:
        db['access_logs'].insert_one({
            "user_id": user_id,
            "movie": movie_name,
            "timestamp": time.time(),
            "sent": False
        })
    except Exception:
        pass


def get_unsent_logs(limit=20):
    try:
        return list(db['access_logs'].find({"sent": False}).limit(limit))
    except Exception:
        return []


def mark_log_sent(log_id):
    try:
        db['access_logs'].update_one(
            {"_id": log_id},
            {"$set": {"sent": True}}
        )
    except Exception:
        pass


# ================= TTL INDEX =================

def setup_log_ttl():
    try:
        db['access_logs'].create_index(
            "timestamp",
            expireAfterSeconds=7 * 24 * 60 * 60  # 7 days
        )
    except Exception:
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
    except Exception:
        return 0
