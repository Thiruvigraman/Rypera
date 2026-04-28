# file: commands/upload_movie.py

import time
import threading

from database import save_movie, load_movies
from bot import send_message
from webhook import log_to_discord
from config import BOT_USERNAME
from utils import get_username

PENDING_UPLOAD = {}
TIMEOUT = 60


def handle_upload(chat_id, message, user):
    doc = message.get("document")

    if not doc:
        return send_message(chat_id, "Send a file to upload")

    file_id = doc["file_id"]

    PENDING_UPLOAD[chat_id] = {
        "file_id": file_id,
        "time": time.time()
    }

    send_message(chat_id, "📥 File received\n\nSend movie name within 60 sec")

    def expire():
        time.sleep(TIMEOUT)

        data = PENDING_UPLOAD.get(chat_id)

        if data and time.time() - data["time"] >= TIMEOUT:
            PENDING_UPLOAD.pop(chat_id, None)
            send_message(chat_id, "⏰ Upload cancelled (timeout)")

    threading.Thread(target=expire, daemon=True).start()


def handle_upload_name(chat_id, text, user):
    data = PENDING_UPLOAD.get(chat_id)

    if not data:
        return False

    # timeout safety
    if time.time() - data["time"] > TIMEOUT:
        PENDING_UPLOAD.pop(chat_id, None)
        send_message(chat_id, "⏰ Upload expired, send file again")
        return True

    movie_name = text.strip()

    movies = load_movies()

    # duplicate protection (FIXED)
    if movie_name in movies:
        send_message(chat_id, "❌ Movie name already exists\nTry different name")

        PENDING_UPLOAD.pop(chat_id, None)  # prevent stuck state
        return True

    token = save_movie(movie_name, data["file_id"])

    if not token:
        send_message(chat_id, "❌ Save failed")
        return True

    PENDING_UPLOAD.pop(chat_id, None)

    link = f"https://t.me/{BOT_USERNAME}?start={token}"

    send_message(
        chat_id,
        f"✅ Saved file name : {movie_name}\nGenerated link : 🔗 {link}"
    )

    log_to_discord(
        "📤 Movie Uploaded",
        "list",
        "info",
        fields={
            "admin": get_username(user),
            "name": movie_name
        }
    )

    return True