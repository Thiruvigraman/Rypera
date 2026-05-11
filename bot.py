# file: bot.py

import requests
import threading
import time
from collections import defaultdict

from config import BOT_TOKEN, STORAGE_CHAT_ID
from database import save_sent_file, delete_sent_file_record, get_pending_files
from webhook import log_to_discord

session = requests.Session()

# ================= RATE LIMIT =================

USER_LAST_REQUEST = defaultdict(float)
RATE_LIMIT_SECONDS = 0.4


def is_rate_limited(chat_id):
    now = time.time()

    if now - USER_LAST_REQUEST[chat_id] < RATE_LIMIT_SECONDS:
        return True

    USER_LAST_REQUEST[chat_id] = now
    return False


# ================= DUPLICATE SEND GUARD =================

RECENT_SENDS = {}
DUPLICATE_WINDOW = 5  # seconds


def is_duplicate_send(chat_id, file_id):
    key = f"{chat_id}:{file_id}"
    now = time.time()

    if key in RECENT_SENDS and now - RECENT_SENDS[key] < DUPLICATE_WINDOW:
        return True

    RECENT_SENDS[key] = now

    # cleanup memory
    if len(RECENT_SENDS) > 5000:
        RECENT_SENDS.clear()

    return False


# ================= SEND MESSAGE =================

def send_message(
    chat_id,
    text,
    parse_mode=None,
    reply_markup=None,
    skip_rate_limit=False
):
    if not chat_id or not text:
        return {"ok": False}

    if not skip_rate_limit:
        if is_rate_limited(chat_id):
            return {
                "ok": False,
                "rate_limited": True
            }

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if parse_mode:
        payload["parse_mode"] = parse_mode

    # support inline buttons
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        res = session.post(url, json=payload, timeout=10)
        data = res.json()

        if not data.get("ok"):
            error = data.get("description", "")

            if "Forbidden" in error or "blocked" in error:
                return {"ok": False, "ignored": True}

            log_to_discord(
                "Telegram send error",
                "status",
                "error",
                fields={
                    "chat_id": chat_id,
                    "error": error
                }
            )

        return data

    except Exception as e:
        log_to_discord(
            "Telegram send crash",
            "status",
            "error",
            fields={
                "chat_id": chat_id,
                "error": str(e)
            }
        )

        return {"ok": False}

# ================= EDIT MESSAGE =================

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"

    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        res = session.post(url, json=payload, timeout=10)
        data = res.json()

        if not data.get("ok"):
            # ignore harmless error
            if "message is not modified" in data.get("description", ""):
                return

            print("EDIT FAILED:", data)

    except Exception as e:
        print("EDIT ERROR:", str(e))

# ================= STORAGE =================

def forward_file_to_storage(file_id, username=None, movie_name=None, count=None):
    if not STORAGE_CHAT_ID or not file_id:
        return None

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'

    caption_parts = []

    if username:
        caption_parts.append(f"👤 {username}")

    if movie_name:
        caption_parts.append(f"🎬 {movie_name}")

    if count is not None:
        caption_parts.append(f"🔢 Access: {count}")

    caption = "\n".join(caption_parts) if caption_parts else None

    payload = {
        "chat_id": STORAGE_CHAT_ID,
        "document": file_id
    }

    if caption:
        payload["caption"] = caption

    try:
        res = session.post(url, json=payload, timeout=10)
        data = res.json()

        if data.get("ok"):
            return data["result"]["message_id"]

    except Exception:
        log_to_discord("Storage error", "status", "error")

    return None

# ================= SEND FILE =================

def send_file(
    chat_id,
    file_id,
    username=None,
    movie_name=None,
    count=None,
    skip_rate_limit=False,
    skip_duplicate_check=False,
    store=True,
    show_warning=True
):
    if not chat_id or not file_id:
        return {"ok": False}

    # ================= DUPLICATE CHECK =================

    if not skip_duplicate_check:
        if is_duplicate_send(chat_id, file_id):
            return {
                "ok": False,
                "duplicate": True
            }

    # ================= RATE LIMIT =================

    if not skip_rate_limit:
        if is_rate_limited(chat_id):
            return {
                "ok": False,
                "rate_limited": True
            }

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendDocument"
    )

    # ================= STORAGE COPY =================

    if store:
        threading.Thread(
            target=forward_file_to_storage,
            args=(
                file_id,
                username,
                movie_name,
                count
            ),
            daemon=True
        ).start()

    payload = {
        "chat_id": chat_id,
        "document": file_id
    }

    try:
        res = session.post(
            url,
            json=payload,
            timeout=20
        )

        data = res.json()

        # ================= TELEGRAM FAILED =================

        if not data.get("ok"):

            error_description = data.get(
                "description",
                "Unknown error"
            )

            

            # discord log
            log_to_discord(
                "Send file failed",
                "status",
                "error",
                fields={
                    "chat_id": chat_id,
                    "movie": movie_name,
                    "user": username,
                    "file_id": file_id,
                    "error": error_description
                }
            )

            # storage alert
            try:
                from config import STORAGE_CHAT_ID

                send_message(
                    STORAGE_CHAT_ID,
                    (
                        "❌ FILE DELIVERY FAILED\n\n"
                        f"🎬 Movie: {movie_name}\n"
                        f"👤 User: {username}\n"
                        f"🆔 Chat ID: {chat_id}\n"
                        f"📄 File ID: {file_id}\n"
                        f"⚠️ Error: {error_description}"
                    )
                )

            except Exception:
                pass

            return data

        # ================= SUCCESS =================

        file_message_id = (
            data["result"]["message_id"]
        )

        warning_message_id = None

        if show_warning:

            warning_text = (
                "⚠️ IMPORTANT\n\n"
                "⏳ This file will be deleted in 15 minutes.\n\n"
                "📌 Forward it to another chat "
                "to keep it permanently."
            )

            warning_response = send_message(
                chat_id,
                warning_text,
                skip_rate_limit=True
            )

            if (
                warning_response
                and warning_response.get("ok")
            ):
                warning_message_id = (
                    warning_response["result"]["message_id"]
                )

        save_sent_file(
            chat_id,
            file_message_id,
            warning_message_id,
            time.time()
        )

        return data

    # ================= HARD CRASH =================

    except Exception as e:

        print(
            "SEND FILE CRASH:",
            str(e)
        )

        log_to_discord(
            "Send file crash",
            "status",
            "error",
            fields={
                "chat_id": chat_id,
                "movie": movie_name,
                "user": username,
                "file_id": file_id,
                "error": str(e)
            }
        )

        try:
            from config import STORAGE_CHAT_ID

            send_message(
                STORAGE_CHAT_ID,
                (
                    "💥 FILE SEND CRASH\n\n"
                    f"🎬 Movie: {movie_name}\n"
                    f"👤 User: {username}\n"
                    f"📄 File ID: {file_id}\n"
                    f"⚠️ Error: {str(e)}"
                )
            )

        except Exception:
            pass

        return {"ok": False}


# ================= DELETE =================

def delete_user_messages(chat_id, file_message_id, warning_message_id):
    if not isinstance(chat_id, int):
        return

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'

    for msg_id in [file_message_id, warning_message_id]:
        if not msg_id:
            continue

        try:
            res = session.post(
                url,
                json={'chat_id': chat_id, 'message_id': msg_id},
                timeout=10
            ).json()

            if not res.get("ok"):
                log_to_discord(
                    "Delete failed",
                    "status",
                    "warning",
                    fields={
                        "chat_id": chat_id,
                        "message_id": msg_id,
                        "response": str(res)
                    }
                )

        except Exception as e:
            log_to_discord(
                "Delete exception",
                "status",
                "error",
                fields={
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "error": str(e)
                }
            )

    delete_sent_file_record(chat_id, file_message_id)
    


# ================= ANNOUNCEMENT =================

def send_announcement(user_ids, message, parse_mode=None):
    from database import remove_user

    success = 0
    failed = 0
    blocked = 0

    for user_id in user_ids:
        result = send_message(user_id, message, parse_mode)

        if result and result.get("ok"):
            success += 1
        else:
            failed += 1

            if result and result.get("ignored"):
                blocked += 1

                # 🔥 AUTO REMOVE BLOCKED USER
                remove_user(user_id)

                log_to_discord(
                    "User removed (blocked bot)",
                    "list",
                    "warning",
                    fields={"user_id": user_id}
                )

        time.sleep(0.01)

    total = success + failed

    # DISCORD LOG
    log_to_discord(
        "📢 Announcement Sent",
        "list",
        "info",
        fields={
            "Total Users": total,
            "Success": success,
            "Failed": failed,
            "Blocked": blocked
        }
    )

    # STORAGE LOG
    try:
        summary_text = (
            "📢 ANNOUNCEMENT REPORT\n\n"
            f"📝 Message: {message[:100]}\n\n"
            f"👥 Total Users: {total}\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}\n"
            f"🚫 Blocked: {blocked}"
        )

        send_message(STORAGE_CHAT_ID, summary_text)

    except Exception as e:
        log_to_discord(
            "Storage announcement log failed",
            "status",
            "error",
            fields={"error": str(e)}
        )

    return success, failed

