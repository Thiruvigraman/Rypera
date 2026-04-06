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


def is_admin(uid):
    return int(uid) == ADMIN_ID


def safe_send(chat_id, text):
    send_message(chat_id, text)


def process_update(update):
    try:
        if "callback_query" in update:
            query = update["callback_query"]
            data = query["data"]
            user_id = query["from"]["id"]
            chat_id = query["message"]["chat"]["id"]

            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                json={"callback_query_id": query["id"]}
            )

            if data == "delete_confirm" and is_admin(user_id):
                d = PENDING_DELETE.get(user_id)
                if not d:
                    return

                delete_movie(d["movie"])
                PENDING_DELETE.pop(user_id, None)

                safe_send(chat_id, "Deleted")
                return

            if data == "delete_cancel":
                PENDING_DELETE.pop(user_id, None)
                safe_send(chat_id, "Cancelled")
                return

        if "message" not in update:
            return

        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")
        document = msg.get("document")
        video = msg.get("video")

        if not is_admin(user_id):
            add_user(user_id, "user")

        # ===== GENERATE LINK (TOKEN) =====
        if text.startswith("/generate_link") and is_admin(user_id):
            name = text.split(maxsplit=1)[1]
            movies = load_movies()

            if name not in movies:
                safe_send(chat_id, "Movie not found")
                return

            token = movies[name].get("token")
            link = f"https://t.me/{BOT_USERNAME}?start={token}"

            safe_send(chat_id, link)
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
            return

        # ===== UPLOAD =====
        if (document or video) and is_admin(user_id):
            file_id = document["file_id"] if document else video["file_id"]
            TEMP_FILE_IDS[chat_id] = file_id
            safe_send(chat_id, "Send name")
            return

        # ===== SAVE =====
        if chat_id in TEMP_FILE_IDS and is_admin(user_id):
            save_movie(text, TEMP_FILE_IDS[chat_id])
            TEMP_FILE_IDS.pop(chat_id)
            safe_send(chat_id, "Saved")
            return

    except Exception as e:
        log_to_discord("Handler crash", "status", "error")