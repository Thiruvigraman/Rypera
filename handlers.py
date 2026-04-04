# file: handlers.py

from config import ADMIN_ID
from database import load_movies, save_movie, delete_movie, add_user, get_stats
from bot import send_message, send_file
from webhook import log_to_discord
import time
import psutil
from main import start_time
from database import rename_movie

TEMP_FILE_IDS = {}


def get_user_display_name(user):
    username = user.get('username')
    if username:
        return f"@{username}"
    return user.get('first_name', 'User')


def safe_send(chat_id, text):
    result = send_message(chat_id, text)
    if not result or not result.get("ok"):
        log_to_discord(
            "Telegram send failed",
            "status",
            "error",
            fields={"chat_id": chat_id, "response": str(result)}
        )


def process_update(update):
    try:
        if 'message' not in update:
            return

        message = update['message']
        chat_id = message['chat']['id']
        user = message['from']
        user_id = user['id']
        text = message.get('text', '')
        document = message.get('document')
        video = message.get('video')

        display_name = get_user_display_name(user)

        if user_id != ADMIN_ID:
            add_user(user_id, display_name)

        # ===== UPLOAD =====
        if (document or video) and user_id == ADMIN_ID:
            file_id = document['file_id'] if document else video['file_id']
            TEMP_FILE_IDS[chat_id] = file_id

            safe_send(chat_id, "Send movie name")

            log_to_discord("File uploaded", "list", "info")
            return

# ===== RENAME FILE =====
if text.startswith('/rename_file') and user_id == ADMIN_ID:
    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        safe_send(chat_id, "Usage: /rename_file OldName NewName")
    else:
        old_name = parts[1]
        new_name = parts[2]

        success = rename_movie(old_name, new_name)

        if success:
            safe_send(chat_id, f"Renamed '{old_name}' → '{new_name}'")

            log_to_discord(
                "File renamed",
                "list",
                "info",
                fields={
                    "old": old_name,
                    "new": new_name
                }
            )
        else:
            safe_send(chat_id, f"Movie '{old_name}' not found")

            log_to_discord(
                "Rename failed",
                "list",
                "warning",
                fields={"old": old_name}
            )

    return
        # ===== SAVE =====
        if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
            save_movie(text, TEMP_FILE_IDS[chat_id])
            del TEMP_FILE_IDS[chat_id]

            safe_send(chat_id, f"Movie '{text}' added")

            log_to_discord("Movie added", "list", "info")
            return

        # ===== STATS =====
        if text == '/stats' and user_id == ADMIN_ID:
            stats = get_stats()

            msg = f"📊 Stats\n\nMovies: {stats['movie_count']}\nUsers: {stats['user_count']}"
            safe_send(chat_id, msg)

            log_to_discord("Stats checked", "list", "info")
            return

        # ===== HEALTH (FIXED UPTIME) =====
        if text == '/health' and user_id == ADMIN_ID:
            process = psutil.Process()

            mem = process.memory_info().rss / 1024 / 1024
            cpu = process.cpu_percent(interval=0.1)

            uptime = time.time() - start_time
            h = int(uptime // 3600)
            m = int((uptime % 3600) // 60)
            s = int(uptime % 60)

            msg = (
                f"🟢 Health\n\n"
                f"Uptime: {h}h {m}m {s}s\n"
                f"RAM: {mem:.2f} MB\n"
                f"CPU: {cpu:.2f}%"
            )

            safe_send(chat_id, msg)

            log_to_discord("Health checked", "list", "info")
            return

        # ===== START =====
        if text.startswith('/start '):
            movie_name = text.replace('/start ', '').replace('_', ' ')
            movies = load_movies()

            if movie_name in movies:
                send_file(chat_id, movies[movie_name]['file_id'])

                log_to_discord(
                    "File accessed",
                    "access",
                    "info",
                    fields={"user": display_name, "movie": movie_name}
                )
            else:
                safe_send(chat_id, "Movie not found")

                log_to_discord("Access failed", "access", "warning")

    except Exception as e:
        log_to_discord(
            "Handler crash",
            "status",
            "error",
            fields={"error": str(e)}
        )