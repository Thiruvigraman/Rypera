# file : database/connection.py

import time
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from config import MONGODB_URI
from webhook import log_to_discord

MONGO_AVAILABLE = True

client = None
db = None

movies_collection = None
users_collection = None
sent_files_collection = None
access_logs_collection = None

max_retries = 5

for attempt in range(max_retries):
    try:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )

        client.server_info()

        db = client["telegram_bot"]

        movies_collection = db["movies"]
        users_collection = db["users"]
        sent_files_collection = db["sent_files"]
        access_logs_collection = db["access_logs"]

        # ================= INDEXES =================

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

        existing_indexes = movies_collection.index_information()

        if "token_1" not in existing_indexes:
            movies_collection.create_index(
                [("token", 1)],
                unique=True,
                name="token_1"
            )

        log_to_discord(
            "MongoDB connected",
            "status",
            "info"
        )

        break

    except ConnectionFailure:
        MONGO_AVAILABLE = False

        if attempt == max_retries - 1:
            log_to_discord(
                "MongoDB connection failed",
                "status",
                "error"
            )
            raise

        time.sleep(5)