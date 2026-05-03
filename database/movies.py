# file : database/movies.py

import secrets
import string

from webhook import log_to_discord

from redis_client import (
    get_cache,
    set_cache,
    delete_cache,
    REDIS_AVAILABLE
)

from metadata.parser import parse_filename

from .connection import (
    MONGO_AVAILABLE,
    movies_collection
)


# ================= TOKEN =================

def generate_token(length=10):
    chars = string.ascii_letters + string.digits

    return ''.join(
        secrets.choice(chars)
        for _ in range(length)
    )


def generate_unique_token():
    for _ in range(10):
        token = generate_token()

        if not movies_collection.find_one({"token": token}):
            return token

    return generate_token()


# ================= MOVIES =================

def load_movies():
    if not MONGO_AVAILABLE:
        return {}

    try:
        return {
            doc["name"]: {
                "file_id": doc["file_id"],
                "token": doc.get("token"),
                "metadata": doc.get("metadata", {})
            }

            for doc in movies_collection.find(
                {},
                {
                    "name": 1,
                    "file_id": 1,
                    "token": 1,
                    "metadata": 1,
                    "_id": 0
                }
            )
        }

    except Exception as e:
        print("LOAD MOVIES ERROR:", str(e))

        log_to_discord(
            "Load movies failed",
            "status",
            "error",
            fields={
                "error": str(e)
            }
        )

        return {}

def load_movies_full():
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(
            movies_collection.find(
                {},
                {
                    "_id": 0
                }
            )
        )

    except Exception:
        return []

def load_movies_cached():
    return load_movies()


# ================= SAVE =================

def save_movie(name, file_id):
    if not name or not file_id or not MONGO_AVAILABLE:
        return None

    try:
        existing = movies_collection.find_one({
    "name": name
})

         existing = movies_collection.find_one({
            "name": name
        })

        if existing:
            token = existing.get("token")
        else:
            token = generate_unique_token()

        # ================= METADATA
 =================

        metadata = parse_filename(name)

        movies_collection.update_one(
            {"name": name},
            {
                "$set": {
                    "name": name,
                    "file_id": file_id,
                    "token": token,
                    "metadata": metadata
                },

                "$setOnInsert": {
                    "access_count": 0
                }
            },
            upsert=True
        )

        # ================= CACHE =================

        if REDIS_AVAILABLE:

            set_cache(
                f"movie:{name}",
                {
                    "file_id": file_id,
                    "token": token,
                    "metadata": metadata
                },
                ttl=3600
            )

            set_cache(
                f"token:{token}",
                name,
                ttl=3600
            )

        return token

    except Exception as e:
        print("SAVE MOVIE ERROR:", str(e))

        log_to_discord(
            "Save movie failed",
            "status",
            "error",
            fields={
                "movie": name,
                "error": str(e)
            }
        )

        return None


# ================= GET =================

def get_movie_by_token(token):
    if not token:
        return None

    # ================= REDIS =================

    if REDIS_AVAILABLE:

        name = get_cache(f"token:{token}")

        if name:
            movie = get_cache(f"movie:{name}")

            if movie:
                return {
                    "name": name,
                    **movie
                }

    # ================= MONGO =================

    if not MONGO_AVAILABLE:
        return None

    try:
        movie = movies_collection.find_one({
            "token": token
        })

        if movie and REDIS_AVAILABLE:

            name = movie["name"]

            set_cache(
                f"movie:{name}",
                {
                    "file_id": movie["file_id"],
                    "token": movie["token"],
                    "metadata": movie.get("metadata", {})
                },
                ttl=3600
            )

            set_cache(
                f"token:{token}",
                name,
                ttl=3600
            )

        return movie

    except Exception as e:
        print("GET MOVIE ERROR:", str(e))
        return None


# ================= DELETE =================

def delete_movie(name):
    if not MONGO_AVAILABLE:
        return

    try:
        movie = movies_collection.find_one({
            "name": name
        })

        movies_collection.delete_one({
            "name": name
        })

        if REDIS_AVAILABLE and movie:

            delete_cache(f"movie:{name}")
            delete_cache(f"token:{movie.get('token')}")

    except Exception as e:
        print("DELETE MOVIE ERROR:", str(e))


# ================= RENAME =================

def rename_movie(old_name, new_name):
    if not MONGO_AVAILABLE:
        return False

    try:
        movie = movies_collection.find_one({
            "name": old_name
        })

        if not movie:
            return False

        metadata = parse_filename(new_name)

        movies_collection.delete_one({
            "name": old_name
        })

        movies_collection.insert_one({
            "name": new_name,

            "file_id": movie["file_id"],

            "token": movie.get("token"),

            "metadata": metadata,

            "access_count": movie.get("access_count", 0)
        })

        if REDIS_AVAILABLE:

            delete_cache(f"movie:{old_name}")

            set_cache(
                f"movie:{new_name}",
                {
                    "file_id": movie["file_id"],
                    "token": movie.get("token"),
                    "metadata": metadata
                },
                ttl=3600
            )

        return True

    except Exception as e:
        print("RENAME MOVIE ERROR:", str(e))
        return False


# ================= ACCESS =================

def increment_movie_access(name):
    if not MONGO_AVAILABLE:
        return

    try:
        movies_collection.update_one(
            {"name": name},
            {
                "$inc": {
                    "access_count": 1
                }
            },
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