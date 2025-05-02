#bot.py

import requests
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS
from utils import log_to_discord
import time

def send_message(chat_id: int, text: str) -> None:
    """Send a text message to a Telegram chat."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.ok:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Sent message to chat {chat_id}: {text[:50]}...")
                return
            else:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Failed to send message to chat {chat_id}: {response.text}", critical=True)
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Error sending to chat {chat_id}: {str(e)}", critical=True)
            if attempt < 2:
                time.sleep(2)  # Increased delay to avoid rate limits
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Failed to send message to chat {chat_id} after 3 attempts", critical=True)

def send_file(chat_id: int, file_id: str, caption: str = "") -> None:
    """Send a file (document or video) to a Telegram chat."""
    # Check file type first
    file_info_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
    try:
        file_info_response = requests.get(file_info_url, timeout=5)
        if not file_info_response.ok:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Failed to get file info for {file_id}: {file_info_response.text}", critical=True)
            return
        file_path = file_info_response.json()['result']['file_path']
        is_video = file_path.endswith(('.mp4', '.mkv', '.avi'))
        is_document = file_path.endswith(('.pdf', '.doc', '.txt', '.zip'))  # Add more extensions as needed
        if not (is_video or is_document):
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Unsupported file type for {file_id}: {file_path}", critical=True)
            return
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Error getting file info for {file_id}: {str(e)}", critical=True)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/send{'Video' if is_video else 'Document'}"
    payload = {
        "chat_id": chat_id,
        "video" if is_video else "document": file_id,
        "caption": caption[:1000] if caption else None,
        "parse_mode": "Markdown"
    }
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.ok:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Sent {'video' if is_video else 'document'} {file_id} to chat {chat_id} with caption: {caption[:50]}...")
                return
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Failed to send {'video' if is_video else 'document'} {file_id} to chat {chat_id}: {response.text}", critical=True)
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Error sending {'video' if is_video else 'document'} {file_id} to chat {chat_id}: {str(e)}", critical=True)
            if attempt < 2:
                time.sleep(2)  # Increased delay to avoid rate limits
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Failed to send {'video' if is_video else 'document'} {file_id} to chat {chat_id} after 3 attempts", critical=True)