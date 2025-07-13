# telegram.py

import requests
import threading
import time
from config import BOT_TOKEN
from database import save_sent_file, delete_sent_file_record

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
        warning_message_id = warning_response['result']['message_id']

        # Store sent file metadata in MongoDB
        save_sent_file(chat_id, file_message_id, warning_message_id, time.time())

        # Schedule deletion after 15 minutes
        threading.Timer(900, delete_messages, args=[chat_id, file_message_id, warning_message_id]).start()

def delete_messages(chat_id, file_message_id, warning_message_id):
    """Delete file and warning messages and remove from MongoDB."""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'
    for message_id in [file_message_id, warning_message_id]:
        payload = {'chat_id': chat_id, 'message_id': message_id}
        requests.post(url, json=payload)
    delete_sent_file_record(chat_id, file_message_id)

def cleanup_pending_files():
    """Delete files sent within the last 15 minutes on startup."""
    pending_files = get_pending_files(expiry_minutes=15)
    for file_data in pending_files:
        delete_messages(file_data['chat_id'], file_data['file_message_id'], file_data['warning_message_id'])