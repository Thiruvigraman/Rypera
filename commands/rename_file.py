# file: commands/rename_file.py

from database import load_movies, rename_movie
from bot import send_message
from webhook import log_to_discord
from config import BOT_USERNAME
from utils import get_username


def handle_rename(chat_id, text, user):
    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        return send_message(chat_id, "❌ Usage:\n/rename_file old new")

    old_name = parts[1].strip()
    new_name = parts[2].strip()

    movies = load_movies()

    # ❌ old not found
    if old_name not in movies:
        return send_message(chat_id, "❌ Movie not found")

    # 🚫 duplicate protection (NEW FIX)
    if new_name in movies:
        return send_message(chat_id, "❌ Name already exists\nChoose different name")

    success = rename_movie(old_name, new_name)

    if not success:
        return send_message(chat_id, "❌ Rename failed")

    token = movies[old_name].get("token")
    link = f"https://t.me/{BOT_USERNAME}?start={token}" if token else "No link"

    send_message(
        chat_id,
        f"✅ Renamed\n\n🎬 {old_name}\n➡️ {new_name}\n🔗 {link}"
    )

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