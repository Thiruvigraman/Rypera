# file: commands/delete_movie.py

import time
import threading
import requests

from database import load_movies
from bot import send_message
from config import BOT_TOKEN
from webhook import log_to_discord
from utils import get_username
username = get_username(user)


def handle_delete_movie(chat_id, text, user_id, pending_delete, user):
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        return send_message(chat_id, "Usage: /delete_movie MovieName")

    movie = parts[1]
    movies = load_movies()

    if movie not in movies:
        return send_message(chat_id, "Movie not found")

    pending_delete[user_id] = {
        "movie": movie,
        "time": time.time()
    }

    def expire():
        time.sleep(30)
        pending_delete.pop(user_id, None)

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
            "text": f"⚠️ Confirm delete:\n\n🎬 {movie}",
            "reply_markup": keyboard
        },timeout=10
    )


    log_to_discord(
        message="🗑 Delete Requested",
        log_type="list",
        severity="warning",
        fields={
            "admin": username,
            "movie": movie
        }
    )