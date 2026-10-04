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
GROUP_WORKER_THREADS = []
GROUP_WORKER_LOCK = threading.Lock()

WORKER_COUNT = 1

SEND_DELAY = 1.2

MAX_RETRIES = 3

MAX_GROUP_FILES = 300


# Phase 1 diagnostic logging.
# Set GROUP_DEBUG = False after diagnosis to silence [GROUP] queue logs.
GROUP_DEBUG = True


def _group_debug(message):
    if GROUP_DEBUG:
        print(f"[GROUP] {message}", flush=True)


def _worker_alive():
    return any(
        thread.is_alive()
        for thread in GROUP_WORKER_THREADS
    )


def start_group_worker():
    global QUEUE_WORKERS_STARTED
    global GROUP_WORKER_THREADS

    with GROUP_WORKER_LOCK:
        GROUP_WORKER_THREADS = [
            thread
            for thread in GROUP_WORKER_THREADS
            if thread.is_alive()
        ]

        if _worker_alive():
            QUEUE_WORKERS_STARTED = True
            _group_debug("WORKER_ALIVE")
            return True

        # Repair a stale flag after a worker thread dies.
        QUEUE_WORKERS_STARTED = False

        _group_debug(f"WORKER_STARTING count={WORKER_COUNT}")

        for _ in range(WORKER_COUNT):
            thread = threading.Thread(
                target=group_queue_worker,
                daemon=True,
                name="group-delivery-worker"
            )
            thread.start()
            GROUP_WORKER_THREADS.append(thread)

        QUEUE_WORKERS_STARTED = _worker_alive()

        _group_debug(
            f"WORKER_STARTED alive={QUEUE_WORKERS_STARTED}"
        )

        return QUEUE_WORKERS_STARTED


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

    _group_debug(
        f"QUEUE_PUT group={group_name} count={len(files)} chat_id={chat_id}"
    )

    if not start_group_worker():
        _group_debug("WORKER_START_FAILED")
        return False

    GROUP_SEND_QUEUE.put({
        "chat_id": chat_id,
        "files": files,
        "username": username,
        "group_name": group_name,
        "group_token": group_token,
        "timestamp": time.time()
    })

    _group_debug(f"QUEUE_SIZE size={GROUP_SEND_QUEUE.qsize()}")

    # Final safety check: a dead worker must never leave a queued job stranded.
    if not _worker_alive():
        _group_debug("WORKER_DIED_AFTER_QUEUE_RESTARTING")
        start_group_worker()

    return True


def group_queue_worker():
    _group_debug("WORKER_WAITING")

    while True:
        job = None

        try:
            job = GROUP_SEND_QUEUE.get()

            if not job:
                _group_debug("WORKER_EMPTY_JOB")
                continue

            _group_debug(
                f"JOB_RECEIVED group={job.get('group_name')} "
                f"count={len(job.get('files', []))} "
                f"chat_id={job.get('chat_id')}"
            )

            process_group_delivery(job)

            _group_debug(
                f"JOB_COMPLETE group={job.get('group_name')} "
                f"chat_id={job.get('chat_id')}"
            )

        except Exception as e:
            log_to_discord(
                "Group queue worker crash",
                "status",
                "error",
                fields={"error": str(e)}
            )

            _group_debug(f"WORKER_EXCEPTION error={e}")

        finally:
            if job:
                GROUP_SEND_QUEUE.task_done()


def _retry_delay(result, attempt):
    """Return a safe delay for a temporary failure."""
    if result and result.get("telegram_rate_limited"):
        retry_after = result.get("retry_after", 1)
        try:
            return max(1, int(retry_after))
        except (TypeError, ValueError):
            return 1

    # Exponential backoff for temporary network/5xx failures.
    return min(16, 2 ** max(0, attempt - 1))


def _failure_type(result):
    """
    Classify a failed Telegram send.

    Returns:
        "rate_limit"  -> Telegram 429; retry the same file.
        "temporary"   -> network/5xx; retry the same file.
        "permanent"   -> 4xx/application error; do not retry forever.
        "unknown"     -> missing/ambiguous result; retry a few times.
    """
    if not result:
        return "unknown"

    if result.get("telegram_rate_limited"):
        return "rate_limit"

    status_code = result.get("http_status")
    error_code = result.get("error_code")

    if (
        isinstance(status_code, int)
        and status_code == 429
    ) or (
        isinstance(error_code, int)
        and error_code == 429
    ):
        return "rate_limit"

    if (
        isinstance(status_code, int)
        and status_code >= 500
    ) or (
        isinstance(error_code, int)
        and error_code >= 500
    ):
        return "temporary"

    if (
        isinstance(status_code, int)
        and 400 <= status_code < 500
    ) or (
        isinstance(error_code, int)
        and 400 <= error_code < 500
    ):
        return "permanent"

    return "unknown"


def _temporary_failure(result):
    return _failure_type(result) in {
        "rate_limit",
        "temporary",
        "unknown",
    }

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

    _group_debug(
        f"DELIVERY_START group={group_name} count={total} chat_id={chat_id}"
    )

    if group_token:
        try:
            increment_group_access(group_token)
        except Exception as e:
            log_to_discord(
                "Group access increment failed",
                "status",
                "warning",
                fields={
                    "group": group_name,
                    "token": group_token,
                    "error": str(e)
                }
            )

    for index, movie in enumerate(files, start=1):
        file_id = movie.get("file_id")
        movie_name = movie.get("name")

        _group_debug(
            f"FILE_START index={index}/{total} movie={movie_name}"
        )

        if not file_id:
            failed += 1
            log_to_discord(
                "Grouped file missing file_id",
                "status",
                "error",
                fields={
                    "movie": movie_name,
                    "chat_id": chat_id,
                    "group": group_name,
                    "token": group_token
                }
            )
            continue

        delivered = False
        last_result = None
        failure_kind = None

        # IMPORTANT: temporary failures retry this SAME file.
        # Permanent Telegram errors are reported immediately and never
        # retried in a loop.
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = send_file(
                    chat_id,
                    file_id,
                    username=username,
                    movie_name=movie_name,
                    count=index,
                    skip_rate_limit=True,
                    skip_duplicate_check=True,
                    store=False,
                    show_warning=False
                )

                last_result = result

                if result and result.get("ok"):
                    delivered = True
                    success += 1

                    _group_debug(
                        f"FILE_SENT index={index}/{total} movie={movie_name}"
                    )

                    try:
                        increment_movie_access(movie_name)
                    except Exception as e:
                        log_to_discord(
                            "Grouped movie access increment failed",
                            "status",
                            "warning",
                            fields={
                                "movie": movie_name,
                                "error": str(e)
                            }
                        )
                    break

                failure_kind = _failure_type(result)

                # Telegram 429: wait for Telegram's requested time and retry
                # the SAME file.
                if failure_kind == "rate_limit":
                    delay = _retry_delay(result, attempt)

                    log_to_discord(
                        "Grouped file rate limited; retrying same file",
                        "status",
                        "warning",
                        fields={
                            "movie": movie_name,
                            "attempt": attempt,
                            "max_retries": MAX_RETRIES,
                            "retry_after": delay,
                            "chat_id": chat_id,
                            "group": group_name
                        }
                    )
                    time.sleep(delay)
                    continue

                # Telegram 5xx / network-style failures: retry the SAME file.
                if failure_kind in {"temporary", "unknown"}:
                    delay = _retry_delay(result, attempt)

                    log_to_discord(
                        "Grouped file temporary failure; retrying same file",
                        "status",
                        "warning",
                        fields={
                            "movie": movie_name,
                            "attempt": attempt,
                            "max_retries": MAX_RETRIES,
                            "retry_after": delay,
                            "chat_id": chat_id,
                            "group": group_name,
                            "error": (
                                result.get("description", "Unknown error")
                                if isinstance(result, dict)
                                else "No response"
                            )
                        }
                    )
                    time.sleep(delay)
                    continue

                # 4xx/application errors are considered permanent for this
                # delivery attempt. Report them clearly; do not waste retries.
                break

            except Exception as e:
                last_result = {
                    "ok": False,
                    "description": str(e),
                    "exception": True
                }
                failure_kind = "unknown"

                delay = _retry_delay(None, attempt)

                log_to_discord(
                    "Grouped send exception; retrying same file",
                    "status",
                    "warning",
                    fields={
                        "movie": movie_name,
                        "attempt": attempt,
                        "max_retries": MAX_RETRIES,
                        "retry_after": delay,
                        "error": str(e)
                    }
                )
                time.sleep(delay)

        if not delivered:
            failed += 1

            error_description = (
                last_result.get("description", "Unknown delivery error")
                if isinstance(last_result, dict)
                else "Unknown delivery error"
            )

            if failure_kind == "permanent":
                failure_label = "PERMANENT TELEGRAM ERROR"
            elif failure_kind == "rate_limit":
                failure_label = "RATE LIMIT RETRIES EXHAUSTED"
            elif failure_kind in {"temporary", "unknown"}:
                failure_label = "TEMPORARY FAILURE RETRIES EXHAUSTED"
            else:
                failure_label = "DELIVERY FAILURE"

            _group_debug(
                f"FILE_FAILED index={index}/{total} movie={movie_name} "
                f"type={failure_label} error={error_description}"
            )

            log_to_discord(
                "Grouped file send failed",
                "status",
                "error",
                fields={
                    "movie": movie_name,
                    "chat_id": chat_id,
                    "group": group_name,
                    "token": group_token,
                    "failure_type": failure_label,
                    "error": error_description
                }
            )

            error_text = (
                f"❌ {failure_label}\n\n"
                f"🎬 Movie: {movie_name}\n"
                f"📦 Group: {group_name}\n"
                f"🔑 Token: {group_token}\n"
                f"👤 User: {username}\n"
                f"🆔 Chat ID: {chat_id}\n"
                f"⚠️ Error: {error_description}"
            )

            try:
                send_message(
                    STORAGE_CHAT_ID,
                    error_text,
                    skip_rate_limit=True
                )
            except Exception as e:
                log_to_discord(
                    "Group failure alert failed",
                    "status",
                    "warning",
                    fields={"error": str(e)}
                )

        time.sleep(SEND_DELAY)

    if success > 0:
        send_message(
            chat_id,
            (
                "⚠️ IMPORTANT\n\n"
                "⏳ These files will be deleted in 15 minutes.\n\n"
                "📌 Forward them to another "
                "chat to keep permanently."
            ),
            skip_rate_limit=True
        )

    if failed > 0:
        send_message(
            chat_id,
            (
                "⚠️ GROUP DELIVERY FINISHED\n\n"
                f"✅ Delivered: {success}/{total}\n"
                f"❌ Failed: {failed}/{total}\n\n"
                "Some files could not be delivered. "
                "The failed files were reported to the admin."
            ),
            skip_rate_limit=True
        )
    else:
        send_message(
            chat_id,
            (
                "✅ GROUP DELIVERY COMPLETE\n\n"
                f"📦 Delivered: {success}/{total}\n"
                "All files were sent successfully."
            ),
            skip_rate_limit=True
        )

    _group_debug(
        f"DELIVERY_COMPLETE group={group_name} "
        f"success={success} failed={failed} total={total}"
    )

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
