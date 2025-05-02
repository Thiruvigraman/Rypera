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
                time.sleep(1)
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Failed to send message to chat {chat_id} after 3 attempts", critical=True)

def send_file(chat_id: int, file_id: str, caption: str = "") -> None:
    """Send a file (document or video) to a Telegram chat."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"  # Default to document
    payload = {
        "chat_id": chat_id,
        "document": file_id,
        "caption": caption[:1000] if caption else None,  # Telegram caption limit
        "parse_mode": "Markdown"
    }
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.ok:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Sent file {file_id} to chat {chat_id} with caption: {caption[:50]}...")
                return
            else:
                # Try sendVideo if sendDocument fails
                video_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
                video_payload = {
                    "chat_id": chat_id,
                    "video": file_id,
                    "caption": caption[:1000] if caption else None,
                    "parse_mode": "Markdown"
                }
                video_response = requests.post(video_url, json=video_payload, timeout=10)
                if video_response.ok:
                    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Sent video {file_id} to chat {chat_id} with caption: {caption[:50]}...")
                    return
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Failed to send file {file_id} to chat {chat_id}: {response.text}, Video attempt: {video_response.text}", critical=True)
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Error sending file {file_id} to chat {chat_id}: {str(e)}", critical=True)
            if attempt < 2:
                time.sleep(1)
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Failed to send file {file_id} to chat {chat_id} after 3 attempts", critical=True)