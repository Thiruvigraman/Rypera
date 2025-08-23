#bot.py

from config import BOT_TOKEN, STORAGE_CHAT_ID, DISCORD_WEBHOOK_STATUS, DISCORD_WEBHOOK_FILE_ACCESS
from telegram import send_message
from webhook import log_to_discord
import requests
import os

def forward_file_to_storage(file_id, from_chat_id=None, message_id=None):
    if not STORAGE_CHAT_ID:
        log_to_discord(DISCORD_WEBHOOK_STATUS, "STORAGE_CHAT_ID not set, skipping storage", log_type='status', severity='warning')
        return None
    try:
        if from_chat_id and message_id:  # Forwarded file
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/forwardMessage'
            payload = {
                'chat_id': STORAGE_CHAT_ID,
                'from_chat_id': from_chat_id,
                'message_id': message_id
            }
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Forwarding file to storage chat {STORAGE_CHAT_ID}", log_type='status', severity='info')
            response = requests.post(url, json=payload)
            response.raise_for_status()
            message_data = response.json()
            if message_data.get('ok'):
                storage_message_id = message_data['result']['message_id']
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"File forwarded to storage chat {STORAGE_CHAT_ID}", log_type='status', severity='info')
                return storage_message_id
        else:  # New upload
            file_info = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}').json()
            if not file_info.get('ok'):
                log_to_discord(DISCORD_WEBHOOK_STATUS, "Error retrieving file info for upload", log_type='status', severity='error')
                return None
            file_path = file_info['result']['file_path']
            file_url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}'
            file_response = requests.get(file_url)
            file_response.raise_for_status()
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
            files = {'document': ('file', file_response.content)}
            data = {'chat_id': STORAGE_CHAT_ID}
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Uploading file to storage chat {STORAGE_CHAT_ID}", log_type='status', severity='info')
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            message_data = response.json()
            if message_data.get('ok'):
                storage_message_id = message_data['result']['message_id']
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"File uploaded to storage chat {STORAGE_CHAT_ID}", log_type='status', severity='info')
                return storage_message_id
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error storing file in storage chat {STORAGE_CHAT_ID}: {str(e)}", log_type='status', severity='error')
        return None

def send_file(chat_id, file_id):
    try:
        message_data = send_message(chat_id, "Sending your file, it will be deleted in 15 minutes", parse_mode="Markdown")
        message_id = message_data.get('result', {}).get('message_id')
        if message_id:
            from database import save_sent_file
            save_sent_file(chat_id, message_id)
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
        payload = {'chat_id': chat_id, 'document': file_id}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        message_data = response.json()
        if message_data.get('ok'):
            file_message_id = message_data['result']['message_id']
            save_sent_file(chat_id, file_message_id)
            log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"File sent to chat_id {chat_id}, message_id {file_message_id}", log_type='file_access', severity='info')
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error sending file to chat_id {chat_id}: {str(e)}", log_type='status', severity='error')
        send_message(chat_id, f"Error sending file: {str(e)}")

def send_announcement(user_ids, message, parse_mode=None):
    success_count = 0
    failed_count = 0
    for user_id in user_ids:
        try:
            send_message(user_id, message, parse_mode=parse_mode)
            success_count += 1
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Announcement sent to user {user_id}", log_type='status', severity='info')
        except Exception as e:
            failed_count += 1
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Failed to send announcement to user {user_id}: {str(e)}", log_type='status', severity='error')
    return success_count, failed_count