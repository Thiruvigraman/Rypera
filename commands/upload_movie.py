# file: commands/upload_movie.py

from database import save_movie
from bot import send_message
from webhook import log_to_discord
from config import BOT_USERNAME
from utils import get_username

PENDING_UPLOAD = {}  # user_id → file_id


def handle_upload(chat_id, message, user):
    doc = message.get("document")

    if not doc:
        return send_message(chat_id, "❌ Send a file")

    file_id = doc["file_id"]
    user_id = user["id"]

    # store file temporarily
    PENDING_UPLOAD[user_id] = file_id

    send_message(
        chat_id,
        "📥 File received\n\nNow send movie name:"
    )


def handle_upload_name(chat_id, text, user):
    user_id = user["id"]

    if user_id not in PENDING_UPLOAD:
        return False  # not in upload flow

    file_id = PENDING_UPLOAD.pop(user_id)
    name = text.strip()

    token = save_movie(name, file_id)

    if not token:
        return send_message(chat_id, "❌ Save failed")

    link = f"https://t.me/{BOT_USERNAME}?start={token}"

    send_message(
        chat_id,
        f"✅ Saved file name : {name}\n"
        f"Generated link : 🔗 {link}"
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

    return True