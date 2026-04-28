# file: commands/rename_file.py

from database import rename_movie
from bot import send_message
from webhook import log_to_discord
from utils import get_username


def handle_rename(chat_id, text, user):
    try:
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "❌ Usage: /rename_file <old> <new>")
            return

        old_name, new_name = parts[1], parts[2]

        if rename_movie(old_name, new_name):
            send_message(chat_id, f"✅ Renamed:\n{old_name} → {new_name}")

            log_to_discord(
                "✏️ Movie Renamed",
                "list",
                "info",
                fields={
                    "admin": get_username(user),
                    "old": old_name,
                    "new": new_name
                }
            )
        else:
            send_message(chat_id, "❌ Rename failed")

    except Exception:
        send_message(chat_id, "❌ Rename error")