# file: handlers.py

from config import ADMIN_ID, BOT_TOKEN, BOT_USERNAME
from database import (
    load_movies, save_movie, delete_movie,
    add_user, get_stats, rename_movie,
    get_all_users, increment_movie_access,
    get_top_movies, get_movie_by_token,
    get_db_size_mb, is_db_available
)
from bot import send_message, send_file
from webhook import log_to_discord
import time
import psutil
import requests
import threading
from globals import start_time

TEMP_FILE_IDS = {}
PENDING_ANNOUNCEMENT = {}
PENDING_DELETE = {}

# 🔥 NEW
PROCESSED_UPDATES = set()
USER_RATE_LIMIT = {}


# ================= HELPERS =================
def is_admin(user_id):
    return int(user_id) == ADMIN_ID


def get_user_display_name(user):
    if user.get('username'):
        return f"@{user['username']}"
    return user.get('first_name', 'User')


def safe_send(chat_id, text):
    result = send_message(chat_id, text)
    if not result or not result.get("ok"):
        log_to_discord("Telegram send failed", "status", "error")


# ================= MEMORY CLEANUP =================
def cleanup_memory():
    while True:
        time.sleep(300)
        TEMP_FILE_IDS.clear()
        PENDING_ANNOUNCEMENT.clear()
        PENDING_DELETE.clear()
        PROCESSED_UPDATES.clear()
        USER_RATE_LIMIT.clear()


threading.Thread(target=cleanup_memory, daemon=True).start()


# ================= MAIN =================
def process_update(update):
    try:
        if not isinstance(update, dict):
            return

        # 🔥 DUPLICATE UPDATE PROTECTION
        update_id = update.get("update_id")
        if update_id in PROCESSED_UPDATES:
            return

        PROCESSED_UPDATES.add(update_id)

        if len(PROCESSED_UPDATES) > 1000:
            PROCESSED_UPDATES.clear()

        # ================= CALLBACK =================
        if "callback_query" in update:
            query = update["callback_query"]
            data = query.get("data")
            user_id = query["from"]["id"]
            chat_id = query["message"]["chat"]["id"]

            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                json={"callback_query_id": query["id"]}
            )

            # ===== ANNOUNCE CONFIRM =====
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

                    time.sleep(0.05)

                PENDING_ANNOUNCEMENT.pop(user_id, None)

                safe_send(chat_id, f"✅ Announcement sent\n\nSuccess: {success}\nFailed: {failed}")

                log_to_discord(
                    "📢 Announcement Sent",
                    "list",
                    "info",
                    fields={"Success": success, "Failed": failed}
                )
                return

            # ===== ANNOUNCE CANCEL =====
            if data == "announce_cancel" and is_admin(user_id):
                PENDING_ANNOUNCEMENT.pop(user_id, None)
                safe_send(chat_id, "❌ Announcement cancelled")
                return

            # ===== DELETE CONFIRM =====
            if data == "delete_confirm" and is_admin(user_id):
                d = PENDING_DELETE.get(user_id)

                if not d:
                    safe_send(chat_id, "No pending delete")
                    return

                if time.time() - d["time"] > 30:
                    PENDING_DELETE.pop(user_id, None)
                    safe_send(chat_id, "⌛ Delete expired")
                    return

                delete_movie(d["movie"])
                PENDING_DELETE.pop(user_id, None)

                safe_send(chat_id, f"🗑 Deleted '{d['movie']}'")

                log_to_discord(
                    "Movie deleted",
                    "list",
                    "info",
                    fields={"movie": d["movie"]}
                )
                return

            # ===== DELETE CANCEL =====
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

        # 🔥 RATE LIMIT (per user)
        now = time.time()
        last = USER_RATE_LIMIT.get(user_id, 0)

        if now - last < 1:
            return

        USER_RATE_LIMIT[user_id] = now

        text = msg.get("text", "")
        document = msg.get("document")
        video = msg.get("video")

        display_name = get_user_display_name(user)

        if not is_admin(user_id):
            add_user(user_id, display_name)

        # ===== DB SAFETY =====
        if not is_db_available():
            safe_send(chat_id, "⚠️ Database unavailable")
            return

        # ===== GENERATE LINK =====
        if text.startswith("/generate_link") and is_admin(user_id):
            parts = text.split(maxsplit=1)

            if len(parts) < 2:
                safe_send(chat_id, "Usage: /generate_link MovieName")
                return

            movie_name = parts[1]
            movies = load_movies()

            if movie_name not in movies:
                safe_send(chat_id, "Movie not found")
                return

            token = movies[movie_name].get("token")

            if not token:
                safe_send(chat_id, "Token missing")
                return

            link = f"https://t.me/{BOT_USERNAME}?start={token}"

            safe_send(chat_id, f"🔗 {link}")

            log_to_discord("Link generated", "list", "info", fields={"movie": movie_name})
            return

        # ===== ANNOUNCE =====
        if text.startswith("/announce") and is_admin(user_id):
            parts = text.split(maxsplit=1)

            if len(parts) < 2:
                safe_send(chat_id, "Usage: /announce message")
                return

            announcement = parts[1]
            PENDING_ANNOUNCEMENT[user_id] = announcement

            keyboard = {
                "inline_keyboard": [[
                    {"text": "✅ Confirm", "callback_data": "announce_confirm"},
                    {"text": "❌ Cancel", "callback_data": "announce_cancel"}
                ]]
            }

            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"📢 Preview:\n\n{announcement}",
                    "reply_markup": keyboard
                }
            )
            return

        # ===== DELETE =====
        if text.startswith("/delete_movie") and is_admin(user_id):
            parts = text.split(maxsplit=1)

            if len(parts) < 2:
                safe_send(chat_id, "Usage: /delete_movie MovieName")
                return

            movie = parts[1]
            movies = load_movies()

            if movie not in movies:
                safe_send(chat_id, "Movie not found")
                return

            PENDING_DELETE[user_id] = {"movie": movie, "time": time.time()}

            threading.Thread(
                target=lambda: (time.sleep(30), PENDING_DELETE.pop(user_id, None)),
                daemon=True
            ).start()

            keyboard = {
                "inline_keyboard": [[
                    {"text": "✅ Confirm", "callback_data": "delete_confirm"},
                    {"text": "❌ Cancel", "callback_data": "delete_cancel"}
                ]]
            }

            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"Delete '{movie}'?",
                    "reply_markup": keyboard
                }
            )
            return

        # ===== HEALTH =====
        if text == "/health" and is_admin(user_id):
            p = psutil.Process()

            mem = p.memory_info().rss / 1024 / 1024
            cpu = p.cpu_percent(interval=0.1)

            uptime = time.time() - start_time
            h = int(uptime // 3600)
            m = int((uptime % 3600) // 60)
            s = int(uptime % 60)

            db_size = get_db_size_mb()

            msg = (
                f"🟢 Health\n\n"
                f"⏱ Uptime: {h}h {m}m {s}s\n"
                f"🧠 RAM: {mem:.2f} MB\n"
                f"⚡ CPU: {cpu:.2f}%\n"
                f"🗄 MongoDB: {db_size} MB / 512 MB"
            )

            safe_send(chat_id, msg)
            return

        # ===== START =====
        if text.startswith("/start "):
            query = text.split(" ", 1)[1]

            movie = get_movie_by_token(query)

            if movie:
                send_file(chat_id, movie["file_id"])
                increment_movie_access(movie["name"])
                return

            name = query.replace("_", " ")
            movies = load_movies()

            if name in movies:
                send_file(chat_id, movies[name]["file_id"])
                increment_movie_access(name)
                return

            safe_send(chat_id, "❌ Invalid or expired link")

    except Exception as e:
        log_to_discord("Handler crash", "status", "error", fields={"error": str(e)})