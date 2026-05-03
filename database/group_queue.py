# file: database/group_queue.py

import time

from database.connection import (
    MONGO_AVAILABLE,
    db
)

queue_collection = db["delivery_queue"]


# ================= INDEXES =================

try:
    queue_collection.create_index([
        ("status", 1)
    ])

    queue_collection.create_index([
        ("created_at", 1)
    ])

except Exception:
    pass


# ================= CREATE =================

def create_delivery_job(chat_id, token, movies):
    if not MONGO_AVAILABLE:
        return None

    try:
        document = {
            "chat_id": chat_id,

            "token": token,

            "status": "pending",

            "current_index": 0,

            "movies": movies,

            "created_at": time.time(),

            "started_at": None,

            "completed_at": None,

            "failed_reason": None
        }

        result = queue_collection.insert_one(document)

        return str(result.inserted_id)

    except Exception:
        return None


# ================= FETCH =================

def get_pending_job():
    if not MONGO_AVAILABLE:
        return None

    try:
        return queue_collection.find_one_and_update(
            {
                "status": "pending"
            },
            {
                "$set": {
                    "status": "processing",
                    "started_at": time.time()
                }
            }
        )

    except Exception:
        return None


# ================= UPDATE =================

def update_job_progress(job_id, index):
    if not MONGO_AVAILABLE:
        return

    try:
        from bson import ObjectId

        queue_collection.update_one(
            {
                "_id": ObjectId(job_id)
            },
            {
                "$set": {
                    "current_index": index
                }
            }
        )

    except Exception:
        pass


# ================= COMPLETE =================

def complete_job(job_id):
    if not MONGO_AVAILABLE:
        return

    try:
        from bson import ObjectId

        queue_collection.update_one(
            {
                "_id": ObjectId(job_id)
            },
            {
                "$set": {
                    "status": "completed",
                    "completed_at": time.time()
                }
            }
        )

    except Exception:
        pass


# ================= FAIL =================

def fail_job(job_id, reason):
    if not MONGO_AVAILABLE:
        return

    try:
        from bson import ObjectId

        queue_collection.update_one(
            {
                "_id": ObjectId(job_id)
            },
            {
                "$set": {
                    "status": "failed",
                    "failed_reason": reason
                }
            }
        )

    except Exception:
        pass