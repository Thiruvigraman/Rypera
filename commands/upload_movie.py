# file: commands/upload_movie.py

from database import save_movie
from bot import send_message
from webhook import log_to_discord
from config import BOT_USERNAME
from utils import get_username
username = get_username(user)


def handle_upload(chat_id, message, user):
    doc = message.get("document")

    if not doc:
        return send_message(chat_id, "Send a file to upload")

    file_id = doc["file_id"]
    name = doc.get("file_name", "Unnamed")

    token = save_movie(name, file_id)

    if not token:
        return send_message(chat_id, "❌ Save failed")

    link = f"https://t.me/{BOT_USERNAME}?start={token}"

    send_message(chat_id, f"✅ Saved\n\n📁 {name}\n🔗 {link}")

    username = get_username(user)

    log_to_discord(
        "📤 Movie Uploaded",
        "list",
        "info",
        fields={
            "admin": username,
            "name": name,
            "link": link
        }
    )