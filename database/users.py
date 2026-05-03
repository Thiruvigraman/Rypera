# file : database/users.py

from .connection import (
    MONGO_AVAILABLE,
    users_collection
)


# ================= USERS =================

def add_user(user_id, display_name):
    if not MONGO_AVAILABLE:
        return

    try:
        users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "display_name": display_name
                }
            },
            upsert=True
        )

    except Exception:
        pass


def get_all_users():
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(
            users_collection.find(
                {},
                {
                    "user_id": 1,
                    "_id": 0
                }
            )
        )

    except Exception:
        return []


def remove_user(user_id):
    if not MONGO_AVAILABLE:
        return

    try:
        users_collection.delete_one({"user_id": user_id})

    except Exception:
        pass
