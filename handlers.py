# file: handlers.py

from config import ADMIN_ID, BOT_USERNAME
from database import load_movies, save_movie, delete_movie, rename_movie, add_user, get_all_users, get_stats, db
from bot import send_message, send_file, send_announcement
from webhook import log_to_discord
import time
import psutil
import os
from main import start_time

TEMP_FILE_IDS = {}


def get_user_display_name(user):
    username = user.get('username')
    if username:
        return f"@{username}"
    first_name = user.get('first_name', '')
    last_name = user.get('last_name', '')
    return f"{first_name} {last_name}".strip() or "Unknown User"


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

        # Track user
        if user_id != ADMIN_ID:
            add_user(user_id, display_name)

        # ================= ADMIN FILE UPLOAD =================
        if (document or video) and user_id == ADMIN_ID:
            file_id = document['file_id'] if document else video['file_id']
            TEMP_FILE_IDS[chat_id] = file_id

            safe_send(chat_id, "Send movie name")

            log_to_discord(
                "File uploaded (waiting name)",
                "list",
                "info",
                fields={"admin": display_name}
            )
            return

        # ================= SAVE MOVIE =================
        if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
            save_movie(text, TEMP_FILE_IDS[chat_id])
            del TEMP_FILE_IDS[chat_id]

            safe_send(chat_id, f"Movie '{text}' added")

            log_to_discord(
                "Movie added",
                "list",
                "info",
                fields={"admin": display_name, "movie": text}
            )
            return

        # ================= LIST FILES =================
        if text == '/list_files' and user_id == ADMIN_ID:
            movies = load_movies()
            msg = "\n".join(movies.keys()) or "No files"

            safe_send(chat_id, msg)

            log_to_discord("Files listed", "list", "info")
            return

        # ================= DELETE =================
        if text.startswith('/delete_file') and user_id == ADMIN_ID:
            file_name = text.split(maxsplit=1)[1]

            delete_movie(file_name)
            safe_send(chat_id, f"Deleted {file_name}")

            log_to_discord(
                "File deleted",
                "list",
                "warning",
                fields={"file": file_name}
            )
            return

        # ================= STATS =================
        if text == '/stats' and user_id == ADMIN_ID:
            stats = get_stats()

            msg = (
                f"📊 Stats\n\n"
                f"Movies: {stats['movie_count']}\n"
                f"Users: {stats['user_count']}"
            )

            safe_send(chat_id, msg)

            log_to_discord("Stats checked", "list", "info")
            return

        # ================= HEALTH =================
        if text == '/health' and user_id == ADMIN_ID:
            process = psutil.Process()

            mem = process.memory_info().rss / 1024 / 1024
            cpu = process.cpu_percent(interval=0.1)
            uptime = time.time() - start_time

            msg = (
                f"🟢 Health\n\n"
                f"Uptime: {int(uptime)} sec\n"
                f"RAM: {mem:.2f} MB\n"
                f"CPU: {cpu:.2f}%"
            )

            safe_send(chat_id, msg)

            log_to_discord("Health checked", "list", "info")
            return

        # ================= START =================
        if text.startswith('/start '):
            movie_name = text.replace('/start ', '').replace('_', ' ')
            movies = load_movies()

            if movie_name in movies:
                send_file(chat_id, movies[movie_name]['file_id'])

                log_to_discord(
                    "File accessed",
                    "access",
                    "info",
                    fields={
                        "user": display_name,
                        "movie": movie_name
                    }
                )
            else:
                safe_send(chat_id, "Movie not found")

                log_to_discord(
                    "Access failed",
                    "access",
                    "warning",
                    fields={"movie": movie_name}
                )

    except Exception as e:
        log_to_discord(
            "Handler crash",
            "status",
            "error",
            fields={"error": str(e)}
        )