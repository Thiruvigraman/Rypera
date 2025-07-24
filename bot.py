#bot.py

import requests
import threading
import time
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS, STORAGE_CHAT_ID
from database import save_sent_file, delete_sent_file_record, get_pending_files
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
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error sending message to chat {chat_id}: {str(e)}", log_type='status')
        return {'ok': False, 'error': str(e)}

def forward_file_to_storage(file_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    payload = {'chat_id': STORAGE_CHAT_ID, 'document': file_id}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        message_data = response.json()
        if message_data.get('ok'):
            storage_message_id = message_data['result']['message_id']
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"File stored in storage chat {STORAGE_CHAT_ID}", log_type='status')
            return storage_message_id
        else:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Failed to store file in storage chat {STORAGE_CHAT_ID}", log_type='status')
            return None
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error storing file in storage chat {STORAGE_CHAT_ID}: {str(e)}", log_type='status')
        return None

def send_file(chat_id, file_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    # Forward file to storage chat first
    storage_message_id = forward_file_to_storage(file_id)
    if not storage_message_id:
        send_message(chat_id, "Error: Could not store file for sharing.")
        return {'ok': False, 'error': 'Failed to store file'}

    # Send file to user from storage chat
    payload = {'chat_id': chat_id, 'document': file_id}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        message_data = response.json()

        if message_data.get('ok'):
            file_message_id = message_data['result']['message_id']

            warning_text = (
                "❗️ *IMPORTANT* ❗️\n\n"
                "This message will be deleted in *15 minutes*.\n\n"
                "📌 *Forward this file to another chat to keep it downloadable.*"
            )
            warning_response = send_message(chat_id, warning_text, parse_mode="Markdown")
            warning_message_id = warning_response.get('result', {}).get('message_id')

            if warning_message_id:
                save_sent_file(chat_id, file_message_id, warning_message_id, time.time())
                threading.Timer(900, delete_user_messages, args=[chat_id, file_message_id, warning_message_id])
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"File sent to chat {chat_id}", log_type='status')
            else:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error sending warning message to chat {chat_id}", log_type='status')
        return message_data
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error sending file to chat {chat_id}: {str(e)}", log_type='status')
        return {'ok': False, 'error': str(e)}

def delete_user_messages(chat_id, file_message_id, warning_message_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'
    for message_id in [file_message_id, warning_message_id]:
        try:
            payload = {'chat_id': chat_id, 'message_id': message_id}
            response = requests.post(url, json=payload)
            response.raise_for_status()
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Message {message_id} deleted in chat {chat_id}", log_type='status')
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error deleting message {message_id} in chat {chat_id}: {str(e)}", log_type='status')
    delete_sent_file_record(chat_id, file_message_id)

def send_announcement(user_ids, message, parse_mode=None):
    success_count = 0
    failed_count = 0
    for user_id in user_ids:
        try:
            send_message(user_id, message, parse_mode)
            success_count += 1
            time.sleep(0.1)  # Rate limiting
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error sending announcement to user {user_id}: {str(e)}", log_type='status')
            failed_count += 1
    return success_count, failed_count

def cleanup_pending_files():
    try:
        pending_files = get_pending_files(expiry_minutes=15)
        for file_data in pending_files:
            try:
                delete_user_messages(file_data['chat_id'], file_data['file_message_id'], file_data['warning_message_id'])
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"Cleaned up pending file in chat {file_data['chat_id']}", log_type='status')
            except Exception as e:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error cleaning up file in chat {file_data['chat_id']}: {str(e)}", log_type='status')
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error in cleanup_pending_files: {str(e)}", log_type='status')