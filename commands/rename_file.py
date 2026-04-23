# file rename_file.py


from database import rename_movie
from bot import send_message
from webhook import log_to_discord


def handle_rename(chat_id, text):
    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        return send_message(chat_id, "Usage: /rename_file old_name new_name")

    old_name = parts[1]
    new_name = parts[2]

    success = rename_movie(old_name, new_name)

    if success:
        send_message(chat_id, f"✅ Renamed:\n{old_name} → {new_name}")

        log_to_discord(
            "✏️ Movie renamed",
            "list",
            "info",
            fields={"old": old_name, "new": new_name}
        )
    else:
        send_message(chat_id, "❌ Rename failed (movie not found)")