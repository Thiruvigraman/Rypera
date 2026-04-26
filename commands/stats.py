# file: commands/stats.py

from database import get_stats
from bot import send_message
from webhook import log_to_discord
from utils import get_username


def handle_stats(chat_id, user):
    stats = get_stats()
    username = get_username(user)

    msg = f"📊 Stats\n\n🎬 Movies: {stats['movie_count']}\n👤 Users: {stats['user_count']}"
    send_message(chat_id, msg)

    log_to_discord(
        "📊 Stats Viewed",
        "list",
        "info",
        fields={"admin": username}
    )