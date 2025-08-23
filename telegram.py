  #telegram.py

import requests
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS
from webhook import log_to_discord

def send_message(chat_id, text, parse_mode=None):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error sending message to chat {chat_id}: {str(e)}", log_type='status', severity='error')
        return {'ok': False, 'error': str(e)}

def delete_user_messages(chat_id, file_message_id, warning_message_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'
    for message_id in [file_message_id, warning_message_id]:
        try:
            payload = {'chat_id': chat_id, 'message_id': message_id}
            response = requests.post(url, json=payload)
            response.raise_for_status()
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Message {message_id} deleted in chat {chat_id}", log_type='status', severity='info')
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error deleting message {message_id} in chat {chat_id}: {str(e)}", log_type='status', severity='error')