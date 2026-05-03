# file : database/access_logs.py

import time

from .connection import (
    MONGO_AVAILABLE,
    db
)


# ================= ACCESS LOGS =================

def save_access_log(user_id, movie_name):
    if not MONGO_AVAILABLE:
        return

    try:
        db["access_logs"].insert_one({
            "user_id": user_id,
            "movie": movie_name,
            "timestamp": time.time(),
            "sent": False
        })

    except Exception:
        pass


def get_unsent_logs(limit=20):
    try:
        return list(
            db["access_logs"]
            .find({"sent": False})
            .limit(limit)
        )

    except Exception:
        return []


def mark_log_sent(log_id):
    try:
        db["access_logs"].update_one(
            {"_id": log_id},
            {"$set": {"sent": True}}
        )

    except Exception:
        pass


# ================= TTL =================

def setup_log_ttl():
    try:
        db["access_logs"].create_index(
            "timestamp",
            expireAfterSeconds=7 * 24 * 60 * 60
        )

        db["sent_files"].create_index(
            "timestamp",
            expireAfterSeconds=15 * 60
        )

    except Exception:
        pass
