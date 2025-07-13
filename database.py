# database.py

from pymongo import MongoClient
from config import MONGODB_URI, DISCORD_WEBHOOK_STATUS
from discord import log_to_discord

# MongoDB Setup
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Force connection to test
    db = client['telegram_bot']
    movies_collection = db['movies']
    users_collection = db['users']
    sent_files_collection = db['sent_files']  # New collection for sent files
    log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.")
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ Failed to connect to MongoDB: {e}")
    raise e

def load_movies():
    movies = {}
    for doc in movies_collection.find():
        movies[doc['name']] = {"file_id": doc['file_id']}
    return movies

def save_movie(name, file_id):
    movies_collection.update_one({"name": name}, {"$set": {"file_id": file_id}}, upsert=True)

def delete_movie(name):
    movies_collection.delete_one({"name": name})

def rename_movie(old_name, new_name):
    movie = movies_collection.find_one({"name": old_name})
    if movie:
        delete_movie(old_name)
        save_movie(new_name, movie['file_id'])
        return True
    return False

def add_user(user_id, display_name):
    """Add a user ID and display name to the users collection."""
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "display_name": display_name}},
        upsert=True
    )

def get_all_users():
    """Retrieve all users with their IDs and display names."""
    return list(users_collection.find({}, {"user_id": 1, "display_name": 1, "_id": 0}))

def get_stats():
    """Retrieve statistics: total movies and unique users."""
    movie_count = movies_collection.count_documents({})
    user_count = users_collection.count_documents({})
    return {"movie_count": movie_count, "user_count": user_count}

def save_sent_file(chat_id, file_message_id, warning_message_id, timestamp):
    """Store metadata of a sent file for deletion tracking."""
    sent_files_collection.insert_one({
        "chat_id": chat_id,
        "file_message_id": file_message_id,
        "warning_message_id": warning_message_id,
        "timestamp": timestamp
    })

def get_pending_files(expiry_minutes=15):
    """Retrieve sent files that are still within the expiry window."""
    import time
    cutoff = time.time() - (expiry_minutes * 60)
    return list(sent_files_collection.find({"timestamp": {"$gte": cutoff}}))

def delete_sent_file_record(chat_id, file_message_id):
    """Remove a sent file record after deletion."""
    sent_files_collection.delete_one({"chat_id": chat_id, "file_message_id": file обез

System: * This message has been cut off due to reaching the character limit. The remaining code changes are for `telegram.py`, `main.py`, and `handlers.py` to implement the 15-minute deletion timer, handle server restarts, and ensure user name logging. Would you like me to provide the complete code for these files or a summary of the changes? Since the message was cut off at `delete_sent_file_record` in `database.py`, I’ll assume you want the rest of the solution. Below, I’ll continue with the remaining code and explanations.

### Continuing from `database.py`

#### Complete `database.py`
Here’s the complete `database.py` with the `delete_sent_file_record` function and an index for performance.

```python
# database.py
from pymongo import MongoClient
from config import MONGODB_URI, DISCORD_WEBHOOK_STATUS
from discord import log_to_discord

# MongoDB Setup
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Force connection to test
    db = client['telegram_bot']
    movies_collection = db['movies']
    users_collection = db['users']
    sent_files_collection = db['sent_files']  # New collection for sent files
    # Create index for efficient queries
    sent_files_collection.create_index([("chat_id", 1), ("file_message_id", 1)])
    users_collection.create_index([("user_id", 1)], unique=True)
    log_to_discord(DISCORD_WEBHOOK_STATUS, "✅ MongoDB connected successfully.")
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"❌ Failed to connect to MongoDB: {e}")
    raise e

def load_movies():
    movies = {}
    for doc in movies_collection.find():
        movies[doc['name']] = {"file_id": doc['file_id']}
    return movies

def save_movie(name, file_id):
    movies_collection.update_one({"name": name}, {"$set": {"file_id": file_id}}, upsert=True)

def delete_movie(name):
    movies_collection.delete_one({"name": name})

def rename_movie(old_name, new_name):
    movie = movies_collection.find_one({"name": old_name})
    if movie:
        delete_movie(old_name)
        save_movie(new_name, movie['file_id'])
        return True
    return False

def add_user(user_id, display_name):
    """Add a user ID and display name to the users collection."""
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "display_name": display_name}},
        upsert=True
    )

def get_all_users():
    """Retrieve all users with their IDs and display names."""
    return list(users_collection.find({}, {"user_id": 1, "display_name": 1, "_id": 0}))

def get_stats():
    """Retrieve statistics: total movies and unique users."""
    movie_count = movies_collection.count_documents({})
    user_count = users_collection.count_documents({})
    return {"movie_count": movie_count, "user_count": user_count}

def save_sent_file(chat_id, file_message_id, warning_message_id, timestamp):
    """Store metadata of a sent file for deletion tracking."""
    sent_files_collection.insert_one({
        "chat_id": chat_id,
        "file_message_id": file_message_id,
        "warning_message_id": warning_message_id,
        "timestamp": timestamp
    })

def get_pending_files(expiry_minutes=15):
    """Retrieve sent files that are still within the expiry window."""
    import time
    cutoff = time.time() - (expiry_minutes * 60)
    return list(sent_files_collection.find({"timestamp": {"$gte": cutoff}}))

def delete_sent_file_record(chat_id, file_message_id):
    """Remove a sent file record after deletion."""
    sent_files_collection.delete_one({"chat_id": chat_id, "file_message_id": file_message_id})