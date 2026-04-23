# file top_movies.py


from database import get_top_movies
from bot import send_message
from webhook import log_to_discord


def handle_top_movies(chat_id):
    top = get_top_movies()

    if not top:
        return send_message(chat_id, "No data available")

    msg = "🔥 Top Movies:\n\n"

    for i, movie in enumerate(top, 1):
        msg += f"{i}. {movie['name']} — {movie.get('access_count', 0)} downloads\n"

    send_message(chat_id, msg)

    log_to_discord("Top movies viewed", "list", "info")