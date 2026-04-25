# file: commands/stats.py

from database import get_stats
from bot import send_message
from webhook import log_to_discord


def handle_stats(chat_id):
    stats = get_stats()

    send_message(
        chat_id,
        f"📊 Stats\n\n🎬 {stats['movie_count']}\n👤 {stats['user_count']}"
    )

    log_to_discord(
        message="📊 Stats Viewed",
        log_type="list",
        severity="info"
    )