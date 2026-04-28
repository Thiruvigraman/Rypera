# file: commands/upload_movie.py

from database import save_movie
from bot import send_message
from webhook import log_to_discord
from config import BOT_USERNAME
from utils import get_username


def handle_upload(chat_id, message, user):
    doc = message.get("document")

    if not doc:
        return send_message(chat_id, "❌ Send a file")

    file_id = doc["file_id"]

    # ✅ MANUAL NAME (caption required)
    caption = message.get("caption")

    if not caption:
        return send_message(
            chat_id,
            "❌ Send file with caption\n\nExample:\n`One Piece 1159 720p`",
            parse_mode="Markdown"
        )

    name = caption.strip()

    token = save_movie(name, file_id)

    if not token:
        return send_message(chat_id, "❌ Save failed")

    link = f"https://t.me/{BOT_USERNAME}?start={token}"

    send_message(
        chat_id,
        f"✅ Saved\n\n🎬 {name}\n🔗 {link}"
    )

    log_to_discord(
        "📤 Movie Uploaded",
        "list",
        "info",
        fields={
            "admin": get_username(user),
            "name": name
        }
    )