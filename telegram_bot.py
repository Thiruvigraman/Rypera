# telegram_bot.py

import requests
import threading
import time
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS
from database import save_sent_file, delete_sent_file_record, get_pending_files
from discord import log_to_discord

def send_message(chat_id, text, parse_mode=None):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    response = requests.post(url, json=payload)
    return response.json()

def send_file(chat_id, file_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    payload = {'chat_id': chat_id, 'document': file_id}
    response = requests.post(url, json=payload)
    message_data = response.json()

    if message_data.get('ok'):
        file_message_id = message_data['result']['message_id']

        warning_text = (
            "❗️ *IMPORTANT* ❗️\n\n"
            "This Video / File Will Be Deleted In *15 minutes* _(Due To Copyright Issues)_\n\n"
            "📌 *Please Forward This Video / File To Somewhere Else And Start Downloading There.*"
        )
        warning_response = send_message(chat_id, warning_text, parse_mode="Markdown")
        warning_message_id = warning_response.get('result', {}).get('message_id')

        if warning_message_id:
            save_sent_file(chat_id, file_message_id, warning_message_id, time.time())
            threading.Timer(900, delete_messages, args=[chat_id, file_message_id, warning_message_id]).start()
        else:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Failed to send warning message for chat_id: {chat_id}", log_type='status')

def delete_messages(chat_id, file_message_id, warning_message_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'
    for message_id in [file_message_id, warning_message_id]:
        try:
            payload = {'chat_id': chat_id, 'message_id': message_id}
            requests.post(url, json=payload)
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Failed to delete message {message_id} in chat {chat_id}: {e}", log_type='status')
    delete_sent_file_record(chat_id, file_message_id)

def cleanup_pending_files():
    pending_files = get_pending_files(expiry_minutes=15)
    for file_data in pending_files:
        try:
            delete_messages(file_data['chat_id'], file_data['file_message_id'], file_data['warning_message_id'])
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Cleaned up pending file in chat {file_data['chat_id']} on startup", log_type='status')
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error cleaning up file in chat {file_data['chat_id']}: {e}", log_type='status')

def send_announcement(user_ids, message, parse_mode=None):
    success_count = 0
    failed_count = 0
    for user_id in user_ids:
        try:
            send_message(user_id, message, parse_mode)
            success_count += 1
            time.sleep(0.1)
        except Exception:
            failed_count += 1
    return success_count, failed_count