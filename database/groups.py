# file: database/groups.py

import secrets
import string

from .connection import (
    MONGO_AVAILABLE,
    db
)

groups_collection = db["groups"]


# ================= TOKEN =================

def generate_group_token(length=12):
    chars = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(chars)
        for _ in range(length)
    )


def generate_unique_group_token():
    for _ in range(10):
        token = generate_group_token()

        existing = groups_collection.find_one({
            "token": token
        })

        if not existing:
            return token

    return generate_group_token()


# ================= INDEXES =================

def setup_group_indexes():
    if not MONGO_AVAILABLE:
        return

    try:
        groups_collection.create_index(
            [("token", 1)],
            unique=True
        )

        groups_collection.create_index(
            [("title", 1)]
        )

        groups_collection.create_index(
            [("season", 1)]
        )

        groups_collection.create_index(
            [("arc", 1)]
        )

        groups_collection.create_index(
            [("quality", 1)]
        )

        groups_collection.create_index(
            [("audio", 1)]
        )

    except Exception:
        pass


# ================= CREATE =================

def create_group(group_data):
    if not MONGO_AVAILABLE:
        return None

    token = generate_unique_group_token()

    document = {
        "token": token,

        "title": group_data.get("title"),

        "season": group_data.get("season"),

        "arc": group_data.get("arc"),

        "quality": group_data.get("quality"),

        "audio": group_data.get("audio"),

        "start_episode": group_data.get("start_episode"),

        "end_episode": group_data.get("end_episode"),

        "count": group_data.get("count", 0),

        "file_ids": [
            movie["file_id"]
            for movie in group_data.get("movies", [])
        ]
    }

    groups_collection.insert_one(document)

    return token


# ================= FETCH =================

def get_group_by_token(token):
    if not MONGO_AVAILABLE:
        return None

    return groups_collection.find_one({
        "token": token
    })


def get_all_groups():
    if not MONGO_AVAILABLE:
        return []

    return list(
        groups_collection.find({})
    )


# ================= SEARCH =================

def search_groups(query):
    if not MONGO_AVAILABLE:
        return []

    query = query.lower().strip()

    results = []

    cursor = groups_collection.find({})

    for group in cursor:
        title = (
            group.get("title", "")
            .lower()
            .strip()
        )

        arc = (
            str(group.get("arc", ""))
            .lower()
            .strip()
        )

        if query in title or query in arc:
            results.append(group)

    return results


# ================= EXISTS =================

def group_exists(
    title,
    season,
    quality,
    audio,
    start_episode,
    end_episode
):
    if not MONGO_AVAILABLE:
        return False

    existing = groups_collection.find_one({
        "title": title,
        "season": season,
        "quality": quality,
        "audio": audio,
        "start_episode": start_episode,
        "end_episode": end_episode
    })

    return existing is not None


# ================= DELETE =================

def delete_all_groups():
    if not MONGO_AVAILABLE:
        return

    groups_collection.delete_many({})