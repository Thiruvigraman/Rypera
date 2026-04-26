# file: commands/generate_link.py

from database import load_movies
from bot import send_message
from webhook import log_to_discord
from config import BOT_USERNAME
from utils import get_username


def handle_generate_link(chat_id, text, user):
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        return send_message(chat_id, "Usage: /generate_link MovieName")

    movie_name = parts[1]
    movies = load_movies()

    if movie_name not in movies:
        return send_message(chat_id, "Movie not found")

    token = movies[movie_name].get("token")

    if not token:
        return send_message(chat_id, "⚠️ No token found")

    link = f"https://t.me/{BOT_USERNAME}?start={token}"
    send_message(chat_id, f"🔗 {link}")

    username = get_username(user)

    log_to_discord(
        "🔗 Link Generated",
        "list",
        "info",
        fields={"admin": username, "movie": movie_name, "link": link}
    )