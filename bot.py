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
def send_message(chat_id, text, parse_mode=None):
    if not chat_id or not text:
        return {"ok": False}

    if is_rate_limited(chat_id):
        return {"ok": False, "rate_limited": True}

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}

    if parse_mode:
        payload['parse_mode'] = parse_mode

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
                fields={"chat_id": chat_id, "error": error}
            )

        return data

    except Exception as e:
        log_to_discord(
            "Telegram send crash",
            "status",
            "error",
            fields={"chat_id": chat_id, "error": str(e)}
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
def forward_file_to_storage(file_id):
    if not STORAGE_CHAT_ID or not file_id:
        return None

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    payload = {'chat_id': STORAGE_CHAT_ID, 'document': file_id}

    try:
        res = session.post(url, json=payload, timeout=10)
        data = res.json()

        if data.get('ok'):
            log_to_discord("📦 File stored", "list", "info")
            return data['result']['message_id']

    except Exception as e:
        log_to_discord("Storage error", "status", "error")

    return None


# ================= SEND FILE =================


def send_file(chat_id, file_id):
    if not chat_id or not file_id:
        return {"ok": False}

    if is_duplicate_send(chat_id, file_id):
        return {"ok": False, "duplicate": True}

    if is_rate_limited(chat_id):
        return {"ok": False, "rate_limited": True}

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'

    threading.Thread(
        target=forward_file_to_storage,
        args=(file_id,),
        daemon=True
    ).start()

    payload = {
        'chat_id': chat_id,
        'document': file_id
    }

    try:
        res = session.post(url, json=payload, timeout=10)
        data = res.json()

        if not data.get('ok'):
            log_to_discord(
                "Send file failed",
                "status",
                "error",
                fields={"chat_id": chat_id}
            )
            return data

        
        file_message_id = data['result']['message_id']

        warning_text = (
            "⚠️ IMPORTANT\n\n"
            "⏳ This file will be deleted in 15 minutes.\n\n"
            "📌 Forward it to another chat to keep it permanently."
        )

        # retry send warning
        warning_message_id = None

        for _ in range(3):
            warning_response = send_message(chat_id, warning_text)

            if warning_response and warning_response.get("ok"):
                warning_message_id = warning_response['result']['message_id']
                break

            time.sleep(0.5)

        # ✅ ALWAYS SAVE
        save_sent_file(chat_id, file_message_id, warning_message_id, time.time())

        return data

    except Exception as e:
        log_to_discord("Send file crash", "status", "error")
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

        time.sleep(0.01)

    total = success + failed

    # ================= DISCORD LOG =================

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

    # ================= STORAGE CHAT LOG =================
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

# ================= CLEANUP =================
def cleanup_pending_files():
    try:
        pending_files = get_pending_files()

        for f in pending_files:
            if not f.get("chat_id"):
                continue

            delete_user_messages(
                f['chat_id'],
                f.get('file_message_id'),
                f.get('warning_message_id')
            )

    except Exception as e:
        log_to_discord("Cleanup error", "status", "error")
