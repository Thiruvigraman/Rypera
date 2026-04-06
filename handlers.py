# file: handlers.py

from config import ADMIN_ID, BOT_TOKEN
from database import (
    load_movies, save_movie, delete_movie,
    add_user, get_stats, rename_movie,
    get_all_users, increment_movie_access, get_top_movies
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
        log_to_discord(
            "Telegram send failed",
            "status",
            "error",
            fields={"chat_id": chat_id}
        )


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

                log_to_discord("Announcement cancelled", "list", "warning")
                return

            # ===== DELETE CONFIRM =====
            if data == "delete_confirm" and is_admin(user_id):
                data_obj = PENDING_DELETE.get(user_id)

                if not data_obj:
                    safe_send(chat_id, "No pending delete")
                    return

                if time.time() - data_obj["time"] > 30:
                    PENDING_DELETE.pop(user_id, None)
                    safe_send(chat_id, "⌛ Delete request expired (30s)")

                    log_to_discord("Delete expired", "list", "warning")
                    return

                movie_name = data_obj["movie"]

                delete_movie(movie_name)
                PENDING_DELETE.pop(user_id, None)

                safe_send(chat_id, f"🗑 Deleted '{movie_name}'")

                log_to_discord(
                    "🗑 Movie Deleted",
                    "list",
                    "info",
                    fields={"Movie": movie_name}
                )
                return

            # ===== DELETE CANCEL =====
            if data == "delete_cancel" and is_admin(user_id):
                PENDING_DELETE.pop(user_id, None)

                safe_send(chat_id, "❌ Delete cancelled")

                log_to_discord("Delete cancelled", "list", "warning")
                return

        # ================= MESSAGE =================
        if "message" not in update:
            return

        message = update["message"]
        chat_id = message["chat"]["id"]
        user = message["from"]
        user_id = user["id"]

        text = message.get("text", "")
        document = message.get("document")
        video = message.get("video")

        display_name = get_user_display_name(user)

        if not is_admin(user_id):
            add_user(user_id, display_name)

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

            log_to_discord("Announcement preview created", "list", "info")
            return

        # ===== DELETE MOVIE (SAFE) =====
        if text.startswith("/delete_movie") and is_admin(user_id):
            parts = text.split(maxsplit=1)

            if len(parts) < 2:
                safe_send(chat_id, "Usage: /delete_movie MovieName")
                return

            movie_name = parts[1]
            movies = load_movies()

            if movie_name not in movies:
                safe_send(chat_id, "Movie not found")
                return

            PENDING_DELETE[user_id] = {
                "movie": movie_name,
                "time": time.time()
            }

            # auto expire
            def expire():
                time.sleep(30)
                PENDING_DELETE.pop(user_id, None)

            threading.Thread(target=expire, daemon=True).start()

            keyboard = {
                "inline_keyboard": [[
                    {"text": "✅ Confirm Delete", "callback_data": "delete_confirm"},
                    {"text": "❌ Cancel", "callback_data": "delete_cancel"}
                ]]
            }

            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"⚠️ Confirm delete:\n\n🎬 {movie_name}",
                    "reply_markup": keyboard
                }
            )

            log_to_discord("Delete preview created", "list", "warning")
            return

        # ===== UPLOAD =====
        if (document or video) and is_admin(user_id):
            file_id = document["file_id"] if document else video["file_id"]
            TEMP_FILE_IDS[chat_id] = file_id

            safe_send(chat_id, "Send movie name")
            return

        # ===== SAVE =====
        if is_admin(user_id) and chat_id in TEMP_FILE_IDS and text:
            save_movie(text, TEMP_FILE_IDS[chat_id])
            TEMP_FILE_IDS.pop(chat_id)

            safe_send(chat_id, f"Movie '{text}' added")
            return

        # ===== TOP MOVIES =====
        if text == "/top_movies" and is_admin(user_id):
            top = get_top_movies()

            msg = "🔥 Top Movies:\n\n"
            for i, m in enumerate(top, 1):
                msg += f"{i}. {m['name']} — {m.get('access_count', 0)} downloads\n"

            safe_send(chat_id, msg)
            return

        # ===== STATS =====
        if text == "/stats" and is_admin(user_id):
            s = get_stats()
            safe_send(chat_id, f"Movies: {s['movie_count']}\nUsers: {s['user_count']}")
            return

        # ===== HEALTH =====
        if text == "/health" and is_admin(user_id):
            p = psutil.Process()
            mem = p.memory_info().rss / 1024 / 1024
            cpu = p.cpu_percent(interval=0.1)

            u = time.time() - start_time
            h = int(u // 3600)
            m = int((u % 3600) // 60)
            s = int(u % 60)

            safe_send(chat_id, f"Uptime: {h}h {m}m {s}s\nRAM: {mem:.2f}MB\nCPU: {cpu:.2f}%")
            return

        # ===== START =====
        if text.startswith("/start "):
            name = text.replace("/start ", "").replace("_", " ")
            movies = load_movies()

            if name in movies:
                send_file(chat_id, movies[name]["file_id"])
                increment_movie_access(name)

                log_to_discord(
                    "🎬 File Accessed",
                    "access",
                    "info",
                    fields={"User": display_name, "Movie": name}
                )
            else:
                safe_send(chat_id, "File not found")

    except Exception as e:
        log_to_discord(
            "Handler crash",
            "status",
            "error",
            fields={"error": str(e)}
        )