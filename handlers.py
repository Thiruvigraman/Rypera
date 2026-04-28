# file: handlers.py

from config import ADMIN_IDS, BOT_TOKEN
from database import (
    add_user,
    get_movie_by_token,
    increment_movie_access,
    load_movies_cached,
    is_db_available,
    get_all_users,
    delete_movie,
    save_access_log
)

import webhook
from webhook import (
    log_to_discord,
    set_logging,
    is_logging_enabled,
    clear_all_logs,
    get_log_queue_size,
    set_freeze,
    is_frozen,
    
)

from bot import send_message, send_file
from commands.generate_link import handle_generate_link
from commands.delete_movie import handle_delete_movie
from commands.rename_file import handle_rename
from commands.health import handle_health
from commands.stats import handle_stats
from commands.top_movies import handle_top_movies
from commands.announcement import handle_announcement
from commands.list_movies import handle_list_movies, send_page
from commands.upload_movie import handle_upload
from commands.cmd import handle_cmd

from rate_limiter import is_rate_limited

import time
import requests
from threading import Lock

PROCESSED_UPDATES = set()
UPDATE_LOCK = Lock()

PENDING_DELETE = {}
PENDING_ANNOUNCEMENT = {}

ADMIN_ID_SET = set(map(str, ADMIN_IDS))

def is_admin(user_id):
    return str(user_id) in ADMIN_ID_SET

def get_user_name(user):
    if user.get("username"):
        return f"@{user['username']}"
    return user.get("first_name", "User")


def safe_send(chat_id, text):
    res = send_message(chat_id, text)
    if not res or not res.get("ok"):
        log_to_discord("Send failed", "status", "error", fields={"chat_id": chat_id})


def process_update(update):
    try:
        if not isinstance(update, dict):
            return

        update_id = update.get("update_id")

        # thread-safe dedupe
        with UPDATE_LOCK:
            if update_id in PROCESSED_UPDATES:
                return
            PROCESSED_UPDATES.add(update_id)

            if len(PROCESSED_UPDATES) > 2000:
                PROCESSED_UPDATES.clear()

        # ================= CALLBACK =================
        if "callback_query" in update:
            query = update["callback_query"]
            data = query.get("data")
            user_id = query["from"]["id"]
            chat_id = query["message"]["chat"]["id"]

            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                json={"callback_query_id": query["id"]},
                timeout=5
            )

            if data and data.startswith("list_"):
                try:
                    page = int(data.split("_")[1])
                    message_id = query["message"]["message_id"]
                    send_page(chat_id, page, message_id)
                except Exception as e:
                    log_to_discord("Pagination error", "status", "error", fields={"error": str(e)})
                return

            if data == "announce_confirm" and is_admin(user_id):
                announcement = PENDING_ANNOUNCEMENT.get(user_id)

                if not announcement:
                    safe_send(chat_id, "No pending announcement")
                    return

                users = get_all_users()
                success, failed = 0, 0

                for u in users:
                    res = send_message(u['user_id'], announcement)
                    if res and res.get("ok"):
                        success += 1
                    else:
                        failed += 1
                    time.sleep(0.01)

                PENDING_ANNOUNCEMENT.pop(user_id, None)

                safe_send(chat_id, f"✅ Sent\nSuccess: {success}\nFailed: {failed}")

                log_to_discord(
                    "📢 Announcement sent",
                    "list",
                    "info",
                    fields={"success": success, "failed": failed}
                )
                return

            if data == "announce_cancel" and is_admin(user_id):
                PENDING_ANNOUNCEMENT.pop(user_id, None)
                safe_send(chat_id, "❌ Announcement cancelled")
                return

            if data == "delete_confirm" and is_admin(user_id):
                d = PENDING_DELETE.get(user_id)

                if not d:
                    safe_send(chat_id, "No pending delete")
                    return

                delete_movie(d["movie"])
                PENDING_DELETE.pop(user_id, None)

                safe_send(chat_id, f"🗑 Deleted: {d['movie']}")

                log_to_discord(
                    "Movie deleted",
                    "list",
                    "info",
                    fields={"movie": d["movie"]}
                )
                return

            if data == "delete_cancel" and is_admin(user_id):
                PENDING_DELETE.pop(user_id, None)
                safe_send(chat_id, "❌ Cancelled")
                return

        # ================= MESSAGE =================
        if "message" not in update:
            return

        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user = msg["from"]
        user_id = user["id"]

        # ✅ SET ADMIN ALERT TARGET
        if is_admin(user_id):
            webhook.ADMIN_ALERT_CHAT_ID = chat_id

        if "document" in msg and is_admin(user_id):
            handle_upload(chat_id, msg, user)
            return

        if not is_admin(user_id) and is_rate_limited(user_id):
           return

        text = (msg.get("text") or "").strip()

        if not is_admin(user_id):
            add_user(user_id, user.get("first_name", "User"))

        if not text and not is_admin(user_id):
            return


        if not is_db_available():
            safe_send(chat_id, "⚠️ Database unavailable")
            return

# ================= COMMANDS =================

        if is_admin(user_id):

            if text == "/cmd":
                handle_cmd(chat_id)
                return

            if text.startswith("/generate_link"):
                handle_generate_link(chat_id, text, user)
                return

            if text.startswith("/delete_movie"):
                handle_delete_movie(chat_id, text, user_id, PENDING_DELETE, user)
                return

            if text.startswith("/rename_file"):
                handle_rename(chat_id, text, user)
                return

            if text.startswith("/announce"):
                handle_announcement(chat_id, text, user_id, PENDING_ANNOUNCEMENT, user)
                return

            if text == "/stats":
                handle_stats(chat_id, user)
                return

            if text == "/top_movies":
                handle_top_movies(chat_id, user)
                return

            if text == "/health":
                handle_health(chat_id, user)
                return

            if text == "/list_movies":
                handle_list_movies(chat_id, user)
                return

            # ================= LOG COMMANDS =================

            if text == "/pause_logs":
                set_logging(False)
                send_message(chat_id, "🛑 Logging paused")
                return

            if text == "/resume_logs":
                set_logging(True)
                send_message(chat_id, "✅ Logging resumed")
                return

            if text.startswith("/freeze_logs"):
                parts = text.split()
                duration = 3600

                if len(parts) > 1:
                    try:
                        duration = int(parts[1]) * 60
                    except:
                        pass

                set_freeze(True, duration, reason="Manual")
                send_message(chat_id, f"🧊 Logs frozen for {duration//60} min")
                return

            if text == "/unfreeze_logs":
                set_freeze(False)
                send_message(chat_id, "🔥 Logs resumed")
                return

            if text == "/log_status":
                status = "ON" if is_logging_enabled() else "OFF"
                freeze = "FROZEN ❄️" if is_frozen() else "ACTIVE 🔥"
                queue_size = get_log_queue_size()
                reason = getattr(webhook, "FREEZE_REASON", None) or "—"

                send_message(
                    chat_id,
                    f"📊 Logging: {status}\n"
                    f"🧊 Mode: {freeze}\n"
                    f"📛 Reason: {reason}\n"
                    f"📦 Queue: {queue_size}"
                )
                return

            if text == "/clear_logs":
                cleared_queue, failed_count = clear_all_logs()

                send_message(
                    chat_id,
                    f"🧹 Logs cleared\n"
                    f"📦 Queue Cleared: {cleared_queue}\n"
                    f"⚠️ Failed Cleared: {failed_count}"
                )
                return


        # ================= START =================

        if text.startswith("/start "):
            query = text.split(" ", 1)[1]

            movie = get_movie_by_token(query)

            if movie:
                send_file(chat_id, movie["file_id"])
                increment_movie_access(movie["name"])
                save_access_log(user_id, movie["name"])

                log_to_discord(
                    "🎬 File Accessed",
                    "access",
                    "info",
                    fields={
                        "User": get_user_name(user),
                        "User ID": user_id,
                        "Movie": movie["name"]
                    }
                )
                return

            name = query.replace("_", " ")
            movies = load_movies_cached()

            if name in movies:
                send_file(chat_id, movies[name]["file_id"])
                increment_movie_access(name)
                save_access_log(user_id, name)
                return

            safe_send(chat_id, "❌ Invalid or expired link")

            log_to_discord(
                "Invalid link attempt",
                "access",
                "warning",
                fields={"user_id": user_id, "query": query}
            )

    except Exception as e:
        log_to_discord(
            "Handler crash",
            "status",
            "error",
            fields={"error": str(e)}
        )