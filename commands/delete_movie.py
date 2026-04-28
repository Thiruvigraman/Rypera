# file: commands/delete_movie.py

import time
import threading

from database import load_movies
from bot import send_message
from webhook import log_to_discord
from utils import get_username


def handle_delete_movie(chat_id, text, user_id, pending_delete, user):
    try:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "❌ Usage: /delete_movie <name>")
            return

        movie = parts[1]
        movies = load_movies()

        if movie not in movies:
            send_message(chat_id, "❌ Movie not found")
            return

        pending_delete[user_id] = {"movie": movie, "time": time.time()}

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

        send_message(chat_id, f"⚠️ Confirm delete:\n\n🎬 {movie}", reply_markup=keyboard)

        log_to_discord(
            "🗑 Delete Requested",
            "list",
            "warning",
            fields={"admin": get_username(user), "movie": movie}
        )

    except Exception:
        send_message(chat_id, "❌ Delete request failed")