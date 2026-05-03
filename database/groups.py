# file: database/groups.py

import time
import secrets
import string

from webhook import log_to_discord
from database.connection import (
    MONGO_AVAILABLE,
    db
)

groups_collection = db["groups"]


# ================= INDEXES =================

try:
    groups_collection.create_index(
        [("token", 1)],
        unique=True
    )

    groups_collection.create_index([
        ("filters.title", 1),
        ("filters.audio", 1),
        ("filters.quality", 1)
    ])

    groups_collection.create_index([
        ("range.start_episode", 1),
        ("range.end_episode", 1)
    ])

    groups_collection.create_index([
        ("enabled", 1)
    ])

except Exception:
    pass


# ================= TOKEN =================

def generate_group_token(length=12):
    chars = string.ascii_letters + string.digits
    return "g_" + "".join(
        secrets.choice(chars)
        for _ in range(length)
    )


def generate_unique_group_token():
    for _ in range(10):
        token = generate_group_token()

        if not groups_collection.find_one({"token": token}):
            return token

    return generate_group_token()


# ================= CREATE =================

def create_group(
    title,
    display_title,
    description,
    filters,
    start_episode,
    end_episode,
    created_by,
    group_type="episode_range"
):
    if not MONGO_AVAILABLE:
        return None

    try:
        token = generate_unique_group_token()

        document = {
            "token": token,

            "type": group_type,

            "created_at": time.time(),

            "created_by": created_by,

            "enabled": True,

            "title": title.lower(),

            "display_title": display_title,

            "description": description,

            "filters": {
                "title": filters.get("title"),
                "audio": filters.get("audio"),
                "quality": filters.get("quality"),
                "season": filters.get("season"),
                "arc": filters.get("arc")
            },

            "range": {
                "start_episode": start_episode,
                "end_episode": end_episode
            },

            "access_count": 0,

            "last_access": None
        }

        groups_collection.insert_one(document)

        return token

    except Exception as e:
        log_to_discord(
            "Create group failed",
            "status",
            "error",
            fields={
                "error": str(e)
            }
        )

        return None


# ================= GET =================

def get_group_by_token(token):
    if not MONGO_AVAILABLE:
        return None

    try:
        return groups_collection.find_one({
            "token": token,
            "enabled": True
        })

    except Exception:
        return None


# ================= ACCESS =================

def increment_group_access(token):
    if not MONGO_AVAILABLE:
        return

    try:
        groups_collection.update_one(
            {"token": token},
            {
                "$inc": {
                    "access_count": 1
                },
                "$set": {
                    "last_access": time.time()
                }
            }
        )

    except Exception:
        pass


# ================= LIST =================

def get_all_groups():
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(
            groups_collection.find(
                {},
                {
                    "_id": 0
                }
            )
        )

    except Exception:
        return []


# ================= DELETE =================

def delete_group(token):
    if not MONGO_AVAILABLE:
        return False

    try:
        result = groups_collection.delete_one({
            "token": token
        })

        return result.deleted_count > 0

    except Exception:
        return False