# file: database/groups.py

import secrets
import string

from .connection import (
    MONGO_AVAILABLE,
    db
)

groups_collection = db["groups"]


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


def create_group(group_data):
    if not MONGO_AVAILABLE:
        return None

    token = generate_unique_group_token()

    document = {
        "token": token,

        "title": group_data["title"],

        "season": group_data["season"],

        "quality": group_data["quality"],

        "audio": group_data["audio"],

        "start_episode": group_data["start_episode"],

        "end_episode": group_data["end_episode"],

        "count": group_data["count"],

        "file_ids": [
            movie["file_id"]
            for movie in group_data["movies"]
        ]
    }

    groups_collection.insert_one(document)

    return token


def get_group_by_token(token):
    if not MONGO_AVAILABLE:
        return None

    return groups_collection.find_one({
        "token": token
    })


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


def get_all_groups():
    if not MONGO_AVAILABLE:
        return []

    return list(
        groups_collection.find({})
    )