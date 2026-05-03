# file: handlers/upload_handler.py

from commands.upload_movie import (
    handle_upload,
    handle_upload_name
)


def process_upload(
    msg,
    chat_id,
    user,
    user_id,
    is_admin
):
    if not is_admin(user_id):
        return False

    # document upload
    if "document" in msg:
        handle_upload(chat_id, msg, user)
        return True

    text = (msg.get("text") or "").strip()

    # upload naming flow
    if text and not text.startswith("/"):
        if handle_upload_name(chat_id, text, user):
            return True

    return False
