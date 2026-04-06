# file: handlers.py

from config import ADMIN_ID, BOT_TOKEN, BOT_USERNAME
from database import (
    load_movies, save_movie, delete_movie,
    add_user, get_stats, rename_movie,
    get_all_users, increment_movie_access,
    get_top_movies, get_movie_by_token
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


# ================= MAIN =================
def process_update(update):
    try:
        if not isinstance(update, dict):
            return

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

        text = msg.get("text", "")
        document = msg.get("document")
        video = msg.get("video")

        display_name = get_user_display_name(user)

        if not is_admin(user_id):
            add_user(user_id, display_name)

        # ===== GENERATE LINK (TOKEN) =====
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

            log_to_discord(
                "Link generated",
                "list",
                "info",
                fields={"movie": movie_name}
            )
            return

        # ===== ANNOUNCE =====
        if text.startswith("/announce") and is_admin(user_id):
            announcement = text.split(maxsplit=1)[1]
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

        # ===== DELETE MOVIE =====
        if text.startswith("/delete_movie") and is_admin(user_id):
            movie = text.split(maxsplit=1)[1]
            movies = load_movies()

            if movie not in movies:
                safe_send(chat_id, "Movie not found")
                return

            PENDING_DELETE[user_id] = {"movie": movie, "time": time.time()}

            def expire():
                time.sleep(30)
                PENDING_DELETE.pop(user_id, None)

            threading.Thread(target=expire, daemon=True).start()

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

        # ===== RENAME =====
        if text.startswith("/rename_file") and is_admin(user_id):
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                safe_send(chat_id, "Usage: /rename_file old new")
                return

            if rename_movie(parts[1], parts[2]):
                safe_send(chat_id, "Renamed")
            else:
                safe_send(chat_id, "Failed")
            return

        # ===== TOP =====
        if text == "/top_movies" and is_admin(user_id):
            top = get_top_movies()
            msg = "\n".join([f"{i+1}. {m['name']} ({m.get('access_count',0)})" for i,m in enumerate(top)])
            safe_send(chat_id, msg)
            return

        # ===== STATS =====
        if text == "/stats" and is_admin(user_id):
            s = get_stats()
            safe_send(chat_id, f"Movies: {s['movie_count']} | Users: {s['user_count']}")
            return

        # ===== HEALTH =====
        if text == "/health" and is_admin(user_id):
            p = psutil.Process()
            safe_send(chat_id, f"RAM: {p.memory_info().rss/1024/1024:.2f}MB")
            return

        # ===== UPLOAD =====
        if (document or video) and is_admin(user_id):
            file_id = document["file_id"] if document else video["file_id"]
            TEMP_FILE_IDS[chat_id] = file_id
            safe_send(chat_id, "Send name")
            return

        # ===== SAVE =====
        if is_admin(user_id) and chat_id in TEMP_FILE_IDS and text:
            save_movie(text, TEMP_FILE_IDS[chat_id])
            TEMP_FILE_IDS.pop(chat_id)
            safe_send(chat_id, "Saved")
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

            safe_send(chat_id, "Invalid link")

    except Exception as e:
        log_to_discord("Handler crash", "status", "error")