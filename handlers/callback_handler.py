# file: handlers/callback_handler.py

import time
import requests

from config import BOT_TOKEN, BOT_USERNAME

from bot import send_message

from database import (
    get_all_users,
    delete_movie
)

from webhook import log_to_discord

from commands.search import send_search_page
from commands.list_movies import send_page


def process_callback(
    query,
    is_admin,
    safe_send,
    pending_delete,
    pending_announcement
):
    data = query.get("data")

    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
        json={"callback_query_id": query["id"]},
        timeout=5
    )

    # ================= LIST PAGINATION =================

    if data and data.startswith("list_"):
        try:
            page = int(data.split("_")[1])

            message_id = query["message"]["message_id"]

            send_page(chat_id, page, message_id)

        except Exception as e:
            log_to_discord(
                "Pagination error",
                "status",
                "error",
                fields={"error": str(e)}
            )

        return True

    # ================= SEARCH PAGINATION =================

    if data and data.startswith("search_"):
        try:
            page = int(data.split("_")[1])

            message_id = query["message"]["message_id"]

            send_search_page(chat_id, page, message_id)

        except Exception as e:
            log_to_discord(
                "Search pagination error",
                "status",
                "error",
                fields={"error": str(e)}
            )

        return True

    # ================= GET LINK =================

    if data and data.startswith("getlink_"):
        try:
            token = data.split("_", 1)[1]

            link = f"https://t.me/{BOT_USERNAME}?start={token}"

            send_message(chat_id, f"🔗 {link}")

        except Exception as e:
            log_to_discord(
                "Get link error",
                "status",
                "error",
                fields={"error": str(e)}
            )

        return True

    # ================= ANNOUNCEMENT =================

    if data == "announce_confirm" and is_admin(user_id):
        announcement = pending_announcement.get(user_id)

        if not announcement:
            safe_send(chat_id, "No pending announcement")
            return True

        users = get_all_users()

        success = 0
        failed = 0

        for u in users:
            res = send_message(u["user_id"], announcement)

            if res and res.get("ok"):
                success += 1
            else:
                failed += 1

            time.sleep(0.01)

        pending_announcement.pop(user_id, None)

        safe_send(
            chat_id,
            f"✅ Sent\nSuccess: {success}\nFailed: {failed}"
        )

        return True

    if data == "announce_cancel" and is_admin(user_id):
        pending_announcement.pop(user_id, None)

        safe_send(chat_id, "❌ Announcement cancelled")

        return True

    # ================= DELETE =================

    if data == "delete_confirm" and is_admin(user_id):
        d = pending_delete.get(user_id)

        if not d:
            safe_send(chat_id, "No pending delete")
            return True

        delete_movie(d["movie"])

        pending_delete.pop(user_id, None)

        safe_send(chat_id, f"🗑 Deleted: {d['movie']}")

        return True

    if data == "delete_cancel" and is_admin(user_id):
        pending_delete.pop(user_id, None)

        safe_send(chat_id, "❌ Cancelled")

        return True

    return False
