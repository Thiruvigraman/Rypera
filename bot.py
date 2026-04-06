# file: bot.py

import requests
import threading
import time
from config import BOT_TOKEN, STORAGE_CHAT_ID
from database import save_sent_file, delete_sent_file_record, get_pending_files
from webhook import log_to_discord


# ================= SEND MESSAGE =================
def send_message(chat_id, text, parse_mode=None):
    if not chat_id or not text:
        return {"ok": False}

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}

    if parse_mode:
        payload['parse_mode'] = parse_mode

    try:
        res = requests.post(url, json=payload, timeout=10)
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


# ================= STORAGE =================
def forward_file_to_storage(file_id):
    if not STORAGE_CHAT_ID:
        log_to_discord("Storage chat missing", "status", "warning")
        return None

    if not file_id:
        return None

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    payload = {'chat_id': STORAGE_CHAT_ID, 'document': file_id}

    try:
        res = requests.post(url, json=payload, timeout=10)
        data = res.json()

        if data.get('ok'):
            log_to_discord(
                "📦 File stored",
                "access",
                "info",
                fields={"storage_chat": STORAGE_CHAT_ID}
            )
            return data['result']['message_id']

        log_to_discord(
            "Storage failed",
            "access",
            "warning",
            fields={"response": str(data)}
        )

    except Exception as e:
        log_to_discord(
            "Storage error",
            "access",
            "error",
            fields={"error": str(e)}
        )

    return None


# ================= SEND FILE =================
def send_file(chat_id, file_id):
    if not chat_id or not file_id:
        return {"ok": False}

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'

    storage_message_id = forward_file_to_storage(file_id)

    if not storage_message_id:
        log_to_discord("Storage skipped", "access", "warning")

    payload = {'chat_id': chat_id, 'document': file_id}

    try:
        res = requests.post(url, json=payload, timeout=10)
        data = res.json()

        if not data.get('ok'):
            log_to_discord(
                "Send file failed",
                "status",
                "error",
                fields={"chat_id": chat_id, "response": str(data)}
            )
            return data

        file_message_id = data['result']['message_id']

        warning_text = (
            "⚠️ IMPORTANT\n\n"
            "⏳ This file will be deleted in 15 minutes.\n\n"
            "📌 Forward it to another chat to keep it permanently."
        )

        warning_response = send_message(chat_id, warning_text)
        warning_message_id = warning_response.get('result', {}).get('message_id')

        if warning_message_id:
            save_sent_file(chat_id, file_message_id, warning_message_id, time.time())

            threading.Timer(
                900,
                delete_user_messages,
                args=[chat_id, file_message_id, warning_message_id]
            ).start()

        log_to_discord(
            "📤 File Delivered",
            "access",
            "info",
            fields={"chat_id": chat_id}
        )

        return data

    except Exception as e:
        log_to_discord(
            "Send file crash",
            "status",
            "error",
            fields={"chat_id": chat_id, "error": str(e)}
        )
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
            requests.post(
                url,
                json={'chat_id': chat_id, 'message_id': msg_id},
                timeout=10
            )
        except Exception as e:
            log_to_discord(
                "Delete failed",
                "status",
                "error",
                fields={"chat_id": chat_id, "error": str(e)}
            )

    delete_sent_file_record(chat_id, file_message_id)

    log_to_discord(
        "🧹 Cleanup complete",
        "status",
        "info",
        fields={"chat_id": chat_id}
    )


# ================= ANNOUNCEMENT =================
def send_announcement(user_ids, message, parse_mode=None):
    success = 0
    failed = 0

    for user_id in user_ids:
        result = send_message(user_id, message, parse_mode)

        if result and result.get("ok"):
            success += 1
        else:
            failed += 1

        time.sleep(0.05)

    log_to_discord(
        "📢 Announcement Summary",
        "list",
        "info",
        fields={
            "Success": success,
            "Failed": failed,
            "Total": success + failed
        }
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
        log_to_discord(
            "Cleanup error",
            "status",
            "error",
            fields={"error": str(e)}
        )