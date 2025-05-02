#bot.py

import requests
from typing import Dict, Any
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS
from utils import log_to_discord

def send_message(chat_id: int, text: str) -> None:
    """Send a message to a Telegram chat with fallback to plain text."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "MarkdownV2"
    }
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.ok:
                return
            error = response.json()
            log_to_discord(
                DISCORD_WEBHOOK_STATUS,
                f"[send_message] Failed to send message to chat {chat_id}: {error}, Text: {text}",
                critical=True
            )
            # Fallback to plain text if MarkdownV2 parsing fails
            if error.get('error_code') == 400 and "can't parse entities" in error.get('description', ''):
                payload['parse_mode'] = None  # Disable parse_mode for plain text
                response = requests.post(url, json=payload, timeout=10)
                if response.ok:
                    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Succeeded with plain text for chat {chat_id}")
                    return
                log_to_discord(
                    DISCORD_WEBHOOK_STATUS,
                    f"[send_message] Plain text fallback failed for chat {chat_id}: {response.json()}, Text: {text}",
                    critical=True
                )
            if attempt == 2:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Failed to send message to chat {chat_id} after 3 attempts", critical=True)
        except requests.RequestException as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Request error for chat {chat_id}: {str(e)}", critical=True)
            if attempt == 2:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Failed to send message to chat {chat_id} after 3 attempts", critical=True)

def send_file(chat_id: int, file_id: str, caption: str) -> None:
    """Send a file to a Telegram chat."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    payload = {
        "chat_id": chat_id,
        "document": file_id,
        "caption": caption,
        "parse_mode": "MarkdownV2"
    }
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.ok:
                return
            error = response.json()
            log_to_discord(
                DISCORD_WEBHOOK_STATUS,
                f"[send_file] Failed to send file {file_id} to chat {chat_id}: {error}, Caption: {caption}",
                critical=True
            )
            # Fallback to plain text if MarkdownV2 parsing fails
            if error.get('error_code') == 400 and "can't parse entities" in error.get('description', ''):
                payload['parse_mode'] = None
                response = requests.post(url, json=payload, timeout=10)
                if response.ok:
                    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Succeeded with plain text for chat {chat_id}")
                    return
                log_to_discord(
                    DISCORD_WEBHOOK_STATUS,
                    f"[send_file] Plain text fallback failed for chat {chat_id}: {response.json()}, Caption: {caption}",
                    critical=True
                )
            if attempt == 2:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Failed to send file {file_id} to chat {chat_id} after 3 attempts", critical=True)
        except requests.RequestException as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Request error for chat {chat_id}: {str(e)}", critical=True)
            if attempt == 2:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Failed to send file {file_id} to chat {chat_id} after 3 attempts", critical=True)