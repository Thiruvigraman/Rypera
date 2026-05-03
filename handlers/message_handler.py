# file : handlers/message_handler.py

from webhook import log_to_discord

import webhook

from database import (
    add_user,
    is_db_available
)

from rate_limiter import (
    is_rate_limited
)

from handlers.upload_handler import (
    process_upload
)

from handlers.admin_handler import (
    process_admin_commands
)

from handlers.group_start_handler import (
    process_group_start
)


def process_message(
    msg,
    is_admin,
    safe_send,
    pending_delete,
    pending_announcement
):
    chat_id = msg["chat"]["id"]

    user = msg["from"]

    user_id = user["id"]

    text = (msg.get("text") or "").strip()

    if is_admin(user_id):
        webhook.ADMIN_ALERT_CHAT_ID = chat_id

    # ================= UPLOAD =================

    handled = process_upload(
        msg=msg,
        chat_id=chat_id,
        user=user,
        user_id=user_id,
        is_admin=is_admin
    )

    if handled:
        return True

    # ================= RATE LIMIT =================

    if not is_admin(user_id):
        if is_rate_limited(user_id):
            return True

    # ================= REGISTER USER =================

    if not is_admin(user_id):
        add_user(
            user_id,
            user.get("first_name", "User")
        )

    if not text and not is_admin(user_id):
        return True

    if not is_db_available():
        safe_send(
            chat_id,
            "⚠️ Database unavailable"
        )

        return True

    # ================= ADMIN =================

    if is_admin(user_id):

        handled = process_admin_commands(
            text=text,
            chat_id=chat_id,
            user=user,
            user_id=user_id,
            pending_delete=pending_delete,
            pending_announcement=pending_announcement
        )

        if handled:
            return True

    # ================= START =================

    if text.startswith("/start "):

        query = text.split(" ", 1)[1].strip()

        handled = process_group_start(
            token=query,
            chat_id=chat_id,
            user=user
        )

        if handled:
            return True

        safe_send(
            chat_id,
            "❌ Invalid or expired link"
        )

        log_to_discord(
            "Invalid link attempt",
            "access",
            "warning",
            fields={
                "user_id": user_id,
                "query": query
            }
        )

        return True

    return False