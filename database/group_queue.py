# file: database/group_queue.py

import time
import threading
from queue import Queue
from config import STORAGE_CHAT_ID
from bot import send_message

from bot import send_file
from webhook import log_to_discord

GROUP_SEND_QUEUE = Queue()

QUEUE_WORKERS_STARTED = False

WORKER_COUNT = 1

SEND_DELAY = 1.2

MAX_RETRIES = 3

MAX_GROUP_FILES = 300


def start_group_worker():
    global QUEUE_WORKERS_STARTED

    if QUEUE_WORKERS_STARTED:
        return

    QUEUE_WORKERS_STARTED = True

    for _ in range(WORKER_COUNT):
        threading.Thread(
            target=group_queue_worker,
            daemon=True
        ).start()


def queue_group_delivery(
    chat_id,
    files,
    username=None,
    group_name=None,
    group_token=None
):
    if not files:
        return False

    if len(files) > MAX_GROUP_FILES:
        log_to_discord(
            "Group too large",
            "status",
            "warning",
            fields={
                "group": group_name,
                "count": len(files)
            }
        )

        return False

    GROUP_SEND_QUEUE.put({
        "chat_id": chat_id,
        "files": files,
        "username": username,
        "group_name": group_name,
        "group_token": group_token,
        "timestamp": time.time()
    })

    return True


def group_queue_worker():
    while True:
        job = None

        try:
            job = GROUP_SEND_QUEUE.get()

            if not job:
                continue

            process_group_delivery(job)

        except Exception as e:
            log_to_discord(
                "Group queue worker crash",
                "status",
                "error",
                fields={
                    "error": str(e)
                }
            )

        finally:
            if job:
                GROUP_SEND_QUEUE.task_done()


def process_group_delivery(job):
    from database.movies import increment_movie_access
    from database.groups import increment_group_access

    chat_id = job["chat_id"]

    files = job["files"]

    username = job.get("username")

    group_name = job.get("group_name")

    group_token = job.get("group_token")

    total = len(files)

    success = 0

    failed = 0

    if group_token:
        try:
            increment_group_access(group_token)
        except Exception:
            pass

    for index, movie in enumerate(files, start=1):

        file_id = movie.get("file_id")

        movie_name = movie.get("name")

        if not file_id:
            failed += 1
            continue

        delivered = False

        for _ in range(MAX_RETRIES):

            try:
                result = send_file(
                    chat_id,
                    file_id,
                    username=username,
                    movie_name=movie_name,
                    count=index,
                    skip_rate_limit=True,
                    skip_duplicate_check=True,
                    store=False
                )

                if result and result.get("ok"):

                    delivered = True

                    success += 1

                    try:
                        increment_movie_access(movie_name)
                    except Exception:
                        pass

                    break

            except Exception as e:

                log_to_discord(
                    "Grouped send retry failed",
                    "status",
                    "warning",
                    fields={
                        "movie": movie_name,
                        "error": str(e)
                    }
                )

            time.sleep(1)

        if not delivered:

            failed += 1

            log_to_discord(
                "Grouped file send failed",
                "status",
                "warning",
                fields={
                    "movie": movie_name,
                    "chat_id": chat_id,
                    "group": group_name,
                    "token": group_token
                }
            )

            error_text = (
                "❌ GROUP FILE FAILED\n\n"
                f"🎬 Movie: {movie_name}\n"
                f"📦 Group: {group_name}\n"
                f"🔑 Token: {group_token}\n"
                f"👤 User: {username}\n"
                f"🆔 Chat ID: {chat_id}"
            )

            send_message(
                STORAGE_CHAT_ID,
                error_text
            )

        time.sleep(SEND_DELAY)

    log_to_discord(
        "Grouped delivery completed",
        "access",
        "info",
        fields={
            "group": group_name,
            "success": success,
            "failed": failed,
            "total": total,
            "chat_id": chat_id
        }
    )