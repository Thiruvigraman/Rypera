# file : handlers.py

from threading import Lock

from handlers.callback_handler import (
    process_callback
)

from handlers.message_handler import (
    process_message
)

from webhook import (
    log_to_discord
)

from bot import (
    send_message
)

from config import (
    ADMIN_IDS
)

PROCESSED_UPDATES = set()

UPDATE_LOCK = Lock()

PENDING_DELETE = {}

PENDING_ANNOUNCEMENT = {}

ADMIN_ID_SET = set(map(str, ADMIN_IDS))


def is_admin(user_id):
    return str(user_id) in ADMIN_ID_SET


def safe_send(chat_id, text):
    res = send_message(chat_id, text)

    if not res or not res.get("ok"):
        log_to_discord(
            "Send failed",
            "status",
            "error",
            fields={
                "chat_id": chat_id
            }
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

            handled = process_callback(
                query=update["callback_query"],
                is_admin=is_admin,
                safe_send=safe_send,
                pending_delete=PENDING_DELETE,
                pending_announcement=PENDING_ANNOUNCEMENT
            )

            if handled:
                return

        # ================= MESSAGE =================

        if "message" in update:

            handled = process_message(
                msg=update["message"],
                is_admin=is_admin,
                safe_send=safe_send,
                pending_delete=PENDING_DELETE,
                pending_announcement=PENDING_ANNOUNCEMENT
            )

            if handled:
                return

    except Exception as e:
        log_to_discord(
            "Handler crash",
            "status",
            "error",
            fields={
                "error": str(e)
            }
        )