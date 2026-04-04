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
    try:
        username = user.get('username')
        if username:
            return f"@{username}"
        first_name = user.get('first_name', '')
        last_name = user.get('last_name', '')
        return f"{first_name} {last_name}".strip() or "Unknown User"
    except Exception as e:
        log_to_discord(
            "Error retrieving user display name",
            "status",
            "error",
            fields={"error": str(e)}
        )
        return "Unknown User"


def process_update(update):
    try:
        if not isinstance(update, dict) or 'message' not in update:
            log_to_discord("Invalid update received", "status", "error")
            return

        message = update.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        user_id = message.get('from', {}).get('id')
        user = message.get('from', {})
        text = message.get('text', '')
        document = message.get('document')
        video = message.get('video')

        if not chat_id or not user_id:
            log_to_discord("Missing chat_id or user_id", "status", "error")
            return

        display_name = get_user_display_name(user)

        # ===== USER COMMAND =====
        if text:
            log_to_discord(
                "Command received",
                "status",
                "info",
                fields={
                    "User": display_name,
                    "User ID": user_id,
                    "Command": text
                }
            )

        if user_id != ADMIN_ID:
            add_user(user_id, display_name)

        # ===== ADMIN FILE UPLOAD =====
        if (document or video) and user_id == ADMIN_ID:
            file_id = document['file_id'] if document else video['file_id']
            TEMP_FILE_IDS[chat_id] = file_id

            send_message(chat_id, "Send movie name")

            log_to_discord(
                "File uploaded (awaiting name)",
                "list",
                "info",
                fields={
                    "Admin": display_name,
                    "User ID": user_id
                }
            )
            return

        # ===== SAVE MOVIE =====
        if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
            save_movie(text, TEMP_FILE_IDS[chat_id])
            send_message(chat_id, f"Movie '{text}' added")

            log_to_discord(
                "Movie added",
                "list",
                "info",
                fields={
                    "Admin": display_name,
                    "File": text
                },
                force_flush=True
            )

            del TEMP_FILE_IDS[chat_id]
            return

        # ===== LIST FILES =====
        if text == '/list_files' and user_id == ADMIN_ID:
            movies = load_movies()
            msg = "\n".join(movies.keys()) or "No files"

            send_message(chat_id, msg)

            log_to_discord(
                "Files listed",
                "list",
                "info",
                fields={"Admin": display_name}
            )
            return

        # ===== DELETE =====
        if text.startswith('/delete_file') and user_id == ADMIN_ID:
            file_name = text.split(maxsplit=1)[1]
            delete_movie(file_name)

            send_message(chat_id, f"Deleted {file_name}")

            log_to_discord(
                "File deleted",
                "list",
                "warning",
                fields={
                    "Admin": display_name,
                    "File": file_name
                },
                force_flush=True
            )
            return

        # ===== START (USER ACCESS) =====
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
                        "User": display_name,
                        "User ID": user_id,
                        "File": movie_name
                    }
                )
            else:
                send_message(chat_id, "Movie not found")

                log_to_discord(
                    "File access failed",
                    "access",
                    "warning",
                    fields={
                        "User": display_name,
                        "File": movie_name
                    }
                )
            return

    except Exception as e:
        log_to_discord(
            "Processing error",
            "status",
            "error",
            fields={"error": str(e)}
        )