# file: bot.py

import requests
import threading
import time
from config import BOT_TOKEN, STORAGE_CHAT_ID
from database import save_sent_file, delete_sent_file_record, get_pending_files
from webhook import log_to_discord


def send_message(chat_id, text, parse_mode=None):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_to_discord(
            f"Error sending message",
            "status",
            "error",
            fields={"chat_id": chat_id, "error": str(e)}
        )
        return {'ok': False, 'error': str(e)}


def forward_file_to_storage(file_id):
    if not STORAGE_CHAT_ID:
        log_to_discord("STORAGE_CHAT_ID not set", "status", "warning")
        return None

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    payload = {'chat_id': STORAGE_CHAT_ID, 'document': file_id}

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        message_data = response.json()

        if message_data.get('ok'):
            log_to_discord("File stored in storage", "status", "info")
            return message_data['result']['message_id']

    except Exception as e:
        log_to_discord(
            "Storage upload failed",
            "status",
            "error",
            fields={"error": str(e)}
        )
        return None


def send_file(chat_id, file_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'

    storage_message_id = forward_file_to_storage(file_id)

    if not storage_message_id:
        log_to_discord("Storage failed, direct send", "status", "warning")

    payload = {'chat_id': chat_id, 'document': file_id}

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        message_data = response.json()

        if message_data.get('ok'):
            file_message_id = message_data['result']['message_id']

            warning_text = (
                "IMPORTANT\n\n"
                "This message will be deleted in 15 minutes."
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
                    "File sent",
                    "access",
                    "info",
                    fields={"chat_id": chat_id}
                )

            return message_data

    except Exception as e:
        log_to_discord(
            "Send file failed",
            "status",
            "error",
            fields={"chat_id": chat_id, "error": str(e)}
        )


def delete_user_messages(chat_id, file_message_id, warning_message_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'

    for msg_id in [file_message_id, warning_message_id]:
        try:
            requests.post(url, json={'chat_id': chat_id, 'message_id': msg_id}, timeout=10)

            log_to_discord(
                "Message deleted",
                "status",
                "info",
                fields={"chat_id": chat_id, "message_id": msg_id}
            )

        except Exception as e:
            log_to_discord(
                "Delete failed",
                "status",
                "error",
                fields={"error": str(e)}
            )

    delete_sent_file_record(chat_id, file_message_id)


def send_announcement(user_ids, message, parse_mode=None):
    success = 0
    failed = 0

    for user_id in user_ids:
        try:
            send_message(user_id, message, parse_mode)
            success += 1
            time.sleep(0.1)
        except Exception as e:
            failed += 1
            log_to_discord(
                "Announcement failed",
                "status",
                "error",
                fields={"user_id": user_id, "error": str(e)}
            )

    log_to_discord(
        "Announcement summary",
        "list",
        "info",
        fields={"success": success, "failed": failed}
    )

    return success, failed


def cleanup_pending_files():
    try:
        pending_files = get_pending_files()

        for f in pending_files:
            delete_user_messages(
                f['chat_id'],
                f['file_message_id'],
                f['warning_message_id']
            )

            log_to_discord(
                "Cleanup done",
                "status",
                "info",
                fields={"chat_id": f['chat_id']}
            )

    except Exception as e:
        log_to_discord(
            "Cleanup error",
            "status",
            "error",
            fields={"error": str(e)}
        )