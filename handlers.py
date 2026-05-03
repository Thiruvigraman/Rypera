# file: handlers.py

import webhook

from threading import Lock

from config import ADMIN_IDS

from bot import send_message

from database import (
    add_user,
    is_db_available
)

from webhook import log_to_discord

from rate_limiter import is_rate_limited

from handlers.callback_handler import process_callback
from handlers.start_handler import process_start
from handlers.admin_handler import process_admin_commands
from handlers.upload_handler import process_upload


PROCESSED_UPDATES = set()

UPDATE_LOCK = Lock()

PENDING_DELETE = {}

PENDING_ANNOUNCEMENT = {}

ADMIN_ID_SET = set(map(str, ADMIN_IDS))


def is_admin(user_id):
    return str(user_id) in ADMIN_ID_SET


def get_user_name(user):
    if user.get("username"):
        return f"@{user['username']}"

    return user.get("first_name", "User")


def safe_send(chat_id, text):
    res = send_message(chat_id, text)

    if not res or not res.get("ok"):
        log_to_discord(
            "Send failed",
            "status",
            "error",
            fields={"chat_id": chat_id}
        )


def process_update(update):
    try:
        if not isinstance(update, dict):
            return

        update_id = update.get("update_id")

        with UPDATE_LOCK:
            if update_id in PROCESSED_UPDATES:
                return

            PROCESSED_UPDATES.add(update_id)

            if len(PROCESSED_UPDATES) > 2000:
                PROCESSED_UPDATES.clear()

        # ================= CALLBACK =================

        if "callback_query" in update:
            query = update["callback_query"]

            process_callback(
                query=query,
                is_admin=is_admin,
                safe_send=safe_send,
                pending_delete=PENDING_DELETE,
                pending_announcement=PENDING_ANNOUNCEMENT
            )

            return

        # ================= MESSAGE =================

        if "message" not in update:
            return

        msg = update["message"]

        chat_id = msg["chat"]["id"]

        user = msg["from"]

        user_id = user["id"]

        if is_admin(user_id):
            webhook.ADMIN_ALERT_CHAT_ID = chat_id

        # ================= RATE LIMIT =================

        if not is_admin(user_id) and is_rate_limited(user_id):
            return

        text = (msg.get("text") or "").strip()

        # ================= UPLOAD FLOW =================

        handled_upload = process_upload(
            msg=msg,
            chat_id=chat_id,
            user=user,
            user_id=user_id,
            is_admin=is_admin
        )

        if handled_upload:
            return

        # ================= REGISTER USER =================

        if not is_admin(user_id):
            add_user(
                user_id,
                user.get("first_name", "User")
            )

        if not text and not is_admin(user_id):
            return

        # ================= DATABASE =================

        if not is_db_available():
            safe_send(chat_id, "⚠️ Database unavailable")
            return

        # ================= ADMIN COMMANDS =================

        if is_admin(user_id):
            handled = process_admin_commands(
                text=text,
                chat_id=chat_id,
                user=user,
                user_id=user_id,
                pending_delete=PENDING_DELETE,
                pending_announcement=PENDING_ANNOUNCEMENT
            )

            if handled:
                return

        # ================= START =================

        handled = process_start(
            text=text,
            chat_id=chat_id,
            user_id=user_id,
            user=user,
            safe_send=safe_send,
            get_user_name=get_user_name
        )

        if handled:
            return

    except Exception as e:
        log_to_discord(
            "Handler crash",
            "status",
            "error",
            fields={"error": str(e)}
        )