# file: commands/upload_movie.py

from database import save_movie
from bot import send_message
from webhook import log_to_discord
from config import BOT_USERNAME
from utils import get_username


def handle_upload(chat_id, message, user):
    try:
        doc = message.get("document")

        if not doc:
            send_message(chat_id, "❌ Send a file")
            return

        file_id = doc["file_id"]
        name = doc.get("file_name", "Unnamed")

        token = save_movie(name, file_id)

        if not token:
            send_message(chat_id, "❌ Save failed")
            return

        link = f"https://t.me/{BOT_USERNAME}?start={token}"

        send_message(chat_id, f"✅ Saved\n\n📁 {name}\n🔗 {link}")

        log_to_discord(
            "📤 Movie Uploaded",
            "list",
            "info",
            fields={"admin": get_username(user), "name": name}
        )

    except Exception:
        send_message(chat_id, "❌ Upload failed")