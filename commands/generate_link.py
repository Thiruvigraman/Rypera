# file: commands/generate_link.py

from database import load_movies
from bot import send_message
from webhook import log_to_discord
from config import BOT_USERNAME
from utils import get_username


def handle_generate_link(chat_id, text, user):
    try:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "❌ Usage: /generate_link <name>")
            return

        movie_name = parts[1]
        movies = load_movies()

        if movie_name not in movies:
            send_message(chat_id, "❌ Movie not found")
            return

        token = movies[movie_name].get("token")
        if not token:
            send_message(chat_id, "⚠️ No token found")
            return

        link = f"https://t.me/{BOT_USERNAME}?start={token}"
        send_message(chat_id, f"🔗 {link}")

        log_to_discord(
            "🔗 Link Generated",
            "list",
            "info",
            fields={
                "admin": get_username(user),
                "movie": movie_name
            }
        )

    except Exception:
        send_message(chat_id, "❌ Failed to generate link")