# file: commands/rename_file.py

from database import rename_movie
from bot import send_message
from webhook import log_to_discord
from utils import get_username

def handle_rename(chat_id, text, user):
    username = get_username(user)


def handle_rename(chat_id, text, user):
    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        return send_message(chat_id, "Usage: /rename_file old new")

    old_name = parts[1]
    new_name = parts[2]

    if rename_movie(old_name, new_name):
        send_message(chat_id, f"✅ Renamed:\n{old_name} → {new_name}")


        log_to_discord(
            message="✏️ Movie Renamed",
            log_type="list",
            severity="info",
            fields={
                "admin": username,
                "old": old_name,
                "new": new_name
            }
        )
    else:
        send_message(chat_id, "❌ Rename failed")