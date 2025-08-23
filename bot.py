#bot.py

import requests
import threading
import time
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS, STORAGE_CHAT_ID
from database import save_sent_file, delete_sent_file_record
from webhook import log_to_discord

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text, parse_mode=None):
    url = f'{TELEGRAM_API}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error sending message to chat {chat_id}: {str(e)}", log_type='status')
        return {'ok': False, 'error': str(e)}

def forward_file_to_storage(file_id=None, file_path=None):
    """
    Forwards file to storage chat.
    Supports both existing Telegram file_id and local file upload.
    """
    url = f"{TELEGRAM_API}/sendDocument"
    try:
        if file_id:
            payload = {'chat_id': STORAGE_CHAT_ID, 'document': file_id}
            response = requests.post(url, data=payload)
        elif file_path:
            with open(file_path, 'rb') as f:
                files = {'document': f}
                data = {'chat_id': STORAGE_CHAT_ID}
                response = requests.post(url, data=data, files=files)
        else:
            return None

        response.raise_for_status()
        result = response.json()
        if result.get("ok"):
            return result['result']['message_id']
        else:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"File forward failed: {result.get('description', 'Unknown error')}", log_type='status')
            return None
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error in forward_file_to_storage: {str(e)}", log_type='status')
        return None

def send_file(chat_id, file_id):
    """
    Sends file to user and warns it will expire in 15 minutes.
    Also forwards file to storage chat.
    """
    url = f'{TELEGRAM_API}/sendDocument'
    forward_file_to_storage(file_id=file_id)

    payload = {'chat_id': chat_id, 'document': file_id}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        message_data = response.json()

        if message_data.get('ok'):
            file_message_id = message_data['result']['message_id']
            warning_text = (
                "This message will be deleted in 15 minutes.\n"
                "Forward this file to another chat to keep it."
            )
            warning_response = send_message(chat_id, warning_text)
            warning_message_id = warning_response.get('result', {}).get('message_id')

            if warning_message_id:
                save_sent_file(chat_id, file_message_id, warning_message_id, time.time())
                threading.Timer(900, delete_user_messages, args=[chat_id, file_message_id, warning_message_id]).start()
        return message_data
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error sending file: {str(e)}", log_type='status')
        return {'ok': False, 'error': str(e)}

def delete_user_messages(chat_id, file_message_id, warning_message_id):
    url = f'{TELEGRAM_API}/deleteMessage'
    for message_id in [file_message_id, warning_message_id]:
        try:
            requests.post(url, json={'chat_id': chat_id, 'message_id': message_id})
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error deleting message {message_id}: {str(e)}", log_type='status')
    delete_sent_file_record(chat_id, file_message_id)