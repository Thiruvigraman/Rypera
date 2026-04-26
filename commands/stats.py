# file: commands/stats.py

from database import get_stats
from bot import send_message
from webhook import log_to_discord
from utils import get_username

def handle_stats(chat_id, user):
    username = get_username(user)

def handle_stats(chat_id, user):
    stats = get_stats()

    msg = (
        f"📊 Stats\n\n"
        f"🎬 Movies: {stats['movie_count']}\n"
        f"👤 Users: {stats['user_count']}"
    )

    send_message(chat_id, msg)


    log_to_discord(
        message="📊 Stats Viewed",
        log_type="list",
        severity="info",
        fields={
            "admin": username,
            "movies": stats['movie_count'],
            "users": stats['user_count']
        }
    )