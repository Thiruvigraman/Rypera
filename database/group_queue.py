# file: database/group_queue.py

import time
import queue
import threading

from webhook import log_to_discord

from bot import send_file


GROUP_QUEUE = queue.Queue()

ACTIVE_USERS = set()

QUEUE_LOCK = threading.Lock()

WORKER_STARTED = False

MAX_RETRIES = 3

SEND_DELAY = 1.2

BATCH_DELAY = 3


def is_user_active(chat_id):
    with QUEUE_LOCK:
        return chat_id in ACTIVE_USERS


def set_user_active(chat_id):
    with QUEUE_LOCK:
        ACTIVE_USERS.add(chat_id)


def remove_user_active(chat_id):
    with QUEUE_LOCK:
        ACTIVE_USERS.discard(chat_id)


def queue_group_delivery(
    chat_id,
    files,
    username=None
):
    if not files:
        return False

    if is_user_active(chat_id):
        return False

    payload = {
        "chat_id": chat_id,
        "files": files,
        "username": username,
        "created_at": time.time(),
        "retries": 0
    }

    GROUP_QUEUE.put(payload)

    return True


def send_group_files(payload):
    chat_id = payload["chat_id"]

    files = payload["files"]

    username = payload.get("username")

    total = len(files)

    sent = 0

    set_user_active(chat_id)

    try:
        for movie in files:
            try:
                send_file(
                    chat_id=chat_id,
                    file_id=movie["file_id"],
                    username=username,
                    movie_name=movie.get("name"),
                    count=None
                )

                sent += 1

                time.sleep(SEND_DELAY)

            except Exception as e:
                log_to_discord(
                    "Grouped file send failed",
                    "status",
                    "error",
                    fields={
                        "chat_id": chat_id,
                        "movie": movie.get("name"),
                        "error": str(e)
                    }
                )

        log_to_discord(
            "Grouped delivery completed",
            "access",
            "info",
            fields={
                "chat_id": chat_id,
                "total": total,
                "sent": sent
            }
        )

    finally:
        remove_user_active(chat_id)

        time.sleep(BATCH_DELAY)


def worker_loop():
    while True:
        try:
            payload = GROUP_QUEUE.get()

            try:
                send_group_files(payload)

            except Exception as e:
                retries = payload.get("retries", 0)

                if retries < MAX_RETRIES:
                    payload["retries"] = retries + 1
                    GROUP_QUEUE.put(payload)

                log_to_discord(
                    "Group queue worker error",
                    "status",
                    "error",
                    fields={"error": str(e)}
                )

            GROUP_QUEUE.task_done()

        except Exception as e:
            log_to_discord(
                "Group queue crash",
                "status",
                "error",
                fields={"error": str(e)}
            )

            time.sleep(5)


def start_group_queue_worker():
    global WORKER_STARTED

    if WORKER_STARTED:
        return

    WORKER_STARTED = True

    threading.Thread(
        target=worker_loop,
        daemon=True
    ).start()