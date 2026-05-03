# file : database/stats.py

from .connection import (
    MONGO_AVAILABLE,
    db,
    movies_collection,
    users_collection
)


# ================= STATS =================

def get_stats():
    if not MONGO_AVAILABLE:
        return {
            "movie_count": 0,
            "user_count": 0
        }

    try:
        return {
            "movie_count": movies_collection.count_documents({}),
            "user_count": users_collection.count_documents({})
        }

    except Exception:
        return {
            "movie_count": 0,
            "user_count": 0
        }


def get_top_movies(limit=5):
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(
            movies_collection
            .find(
                {},
                {
                    "name": 1,
                    "access_count": 1,
                    "_id": 0
                }
            )
            .sort("access_count", -1)
            .limit(limit)
        )

    except Exception:
        return []


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
