# file: database/groups.py

import secrets
import string

from webhook import log_to_discord

from .connection import (
    MONGO_AVAILABLE,
    groups_collection
)


def generate_group_token(length=12):
    chars = string.ascii_letters + string.digits

    return ''.join(
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

    try:
        title = group_data.get("title")

        season = group_data.get("season")

        arc = group_data.get("arc")

        quality = group_data.get("quality")

        audio = group_data.get("audio")

        start_episode = group_data.get("start_episode")

        end_episode = group_data.get("end_episode")

        existing = groups_collection.find_one({
            "title": title,
            "season": season,
            "arc": arc,
            "quality": quality,
            "audio": audio,
            "start_episode": start_episode,
            "end_episode": end_episode
        })

        if existing:
            return None

        token = generate_unique_group_token()

        document = {
            "title": title,

            "main_title": group_data.get(
                "main_title"
            ),

            "season": season,

            "arc": arc,

            "quality": quality,

            "audio": audio,

            "start_episode": start_episode,

            "end_episode": end_episode,

            "count": group_data.get("count", 0),

            "movies": group_data.get("movies", []),

            "token": token,

            "access_count": 0
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


def get_group_by_token(token):
    if not MONGO_AVAILABLE:
        return None

    try:
        return groups_collection.find_one({
            "token": token
        })

    except Exception:
        return None


def increment_group_access(token):
    if not MONGO_AVAILABLE:
        return

    try:
        groups_collection.update_one(
            {"token": token},
            {"$inc": {"access_count": 1}}
        )

    except Exception:
        pass


def search_groups(query, limit=20):
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(
            groups_collection.find(
                {
                    "title": {
                        "$regex": query,
                        "$options": "i"
                    }
                }
            ).limit(limit)
        )

    except Exception:
        return []


def get_all_groups():
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(
            groups_collection.find().sort(
                "title",
                1
            )
        )

    except Exception:
        return []