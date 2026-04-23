# file stats.py


from database import get_stats
from bot import send_message
from webhook import log_to_discord


def handle_stats(chat_id):
    stats = get_stats()

    msg = (
        f"📊 Stats\n\n"
        f"🎬 Movies: {stats['movie_count']}\n"
        f"👤 Users: {stats['user_count']}"
    )

    send_message(chat_id, msg)

    log_to_discord("Stats viewed", "list", "info")