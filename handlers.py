# file: handlers.py

from config import ADMIN_ID, BOT_TOKEN
from database import (
    add_user, get_movie_by_token,
    increment_movie_access, load_movies,
    is_db_available
)
from bot import send_message, send_file
from webhook import log_to_discord

# 🔥 IMPORT ALL COMMANDS
from commands.generate_link import handle_generate_link
from commands.delete_movie import handle_delete
from commands.rename_file import handle_rename
from commands.health import handle_health
from commands.stats import handle_stats
from commands.top_movies import handle_top
from commands.announcement import handle_announce
from commands.list_movies import handle_list_movies, send_page

import time
import requests

PROCESSED_UPDATES = set()
USER_RATE_LIMIT = {}


# ================= HELPERS =================
def is_admin(user_id):
    try:
        return int(user_id) == int(ADMIN_ID)
    except:
        return False


def safe_send(chat_id, text):
    res = send_message(chat_id, text)
    if not res or not res.get("ok"):
        log_to_discord("Send failed", "status", "error")


# ================= MAIN =================
def process_update(update):
    try:
        if not isinstance(update, dict):
            return

        # ===== DUPLICATE =====
        update_id = update.get("update_id")
        if update_id in PROCESSED_UPDATES:
            return
        PROCESSED_UPDATES.add(update_id)

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

            # 🔥 PAGINATION
            if data and data.startswith("list_"):
                try:
                    page = int(data.split("_")[1])
                    send_page(chat_id, page)
                except Exception as e:
                    log_to_discord("Pagination error", "status", "error")
                return

            # delegate announce/delete confirmations if needed later

        # ================= MESSAGE =================
        if "message" not in update:
            return

        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user = msg["from"]
        user_id = user["id"]

        # ===== RATE LIMIT =====
        now = time.time()
        if now - USER_RATE_LIMIT.get(user_id, 0) < 0.3:
            return
        USER_RATE_LIMIT[user_id] = now

        text = msg.get("text", "")

        # ===== SAVE USER =====
        if not is_admin(user_id):
            add_user(user_id, user.get("first_name", "User"))

        # ===== DB CHECK =====
        if not is_db_available():
            safe_send(chat_id, "⚠️ Database unavailable")
            return

        # ================= COMMAND ROUTER =================

        if text.startswith("/generate_link") and is_admin(user_id):
            handle_generate_link(chat_id, text)
            return

        if text.startswith("/delete_movie") and is_admin(user_id):
            handle_delete(chat_id, text, user_id)
            return

        if text.startswith("/rename_file") and is_admin(user_id):
            handle_rename(chat_id, text)
            return

        if text.startswith("/announce") and is_admin(user_id):
            handle_announce(chat_id, text, user_id)
            return

        if text == "/stats" and is_admin(user_id):
            handle_stats(chat_id)
            return

        if text == "/top_movies" and is_admin(user_id):
            handle_top(chat_id)
            return

        if text == "/health" and is_admin(user_id):
            handle_health(chat_id)
            return

        if text == "/list_movies" and is_admin(user_id):
            handle_list_movies(chat_id)
            return

        # ================= START =================
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
        log_to_discord("Handler crash", "status", "error")