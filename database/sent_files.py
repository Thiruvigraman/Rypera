# file : database/sent_files.py

import time

from .connection import (
    MONGO_AVAILABLE,
    sent_files_collection
)


# ================= FILE CLEAN =================

def save_sent_file(chat_id, file_message_id, warning_message_id, timestamp):
    if not MONGO_AVAILABLE:
        return

    try:
        sent_files_collection.insert_one({
            "chat_id": chat_id,
            "file_message_id": file_message_id,
            "warning_message_id": warning_message_id,
            "timestamp": timestamp
        })

    except Exception:
        pass


def get_pending_files(expiry_minutes=15):
    if not MONGO_AVAILABLE:
        return []

    try:
        cutoff = time.time() - (expiry_minutes * 60)

        return list(
            sent_files_collection.find(
                {
                    "timestamp": {
                        "$lte": cutoff
                    }
                }
            )
        )

    except Exception:
        return []


def delete_sent_file_record(chat_id, file_message_id):
    if not MONGO_AVAILABLE:
        return

    try:
        sent_files_collection.delete_one({
            "chat_id": chat_id,
            "file_message_id": file_message_id
        })

    except Exception:
        pass
