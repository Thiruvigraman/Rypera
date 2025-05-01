# bot.py
import requests
import threading
from typing import Optional, Dict, Any
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS
from utils import log_to_discord

TELEGRAM_API_BASE = f'https://api.telegram.org/bot{BOT_TOKEN}'

def send_message(chat_id: int, text: str, parse_mode: Optional[str] = None) -> Dict[str, Any]:
    """Send a Telegram message to the given chat_id."""
    url = f'{TELEGRAM_API_BASE}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Telegram API error: {e}")
        return {"ok": False, "error": str(e)}

def send_file(chat_id: int, file_id: str) -> None:
    """Send a Telegram document (file) by file_id and schedule deletion in 30 minutes."""
    url = f'{TELEGRAM_API_BASE}/sendDocument'
    payload = {'chat_id': chat_id, 'document': file_id}

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        message_data = response.json()
    except requests.RequestException as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Error: {e}")
        return

    if message_data.get('ok'):
        file_message_id = message_data['result']['message_id']
        warning_text = (
            "❗️ *IMPORTANT* ❗️\n\n"
            "This Video / File Will Be Deleted In *30 minutes* _(Due To Copyright Issues)_\n\n"
            "📌 *Please Forward This Video / File To Somewhere Else And Start Downloading There.*"
        )
        warning_response = send_message(chat_id, warning_text, parse_mode="Markdown")
        warning_message_id = warning_response.get('result', {}).get('message_id')

        # Schedule deletion after 30 minutes (1800 seconds)
        threading.Timer(1800, delete_message, args=[chat_id, file_message_id]).start()
        if warning_message_id:
            threading.Timer(1800, delete_message, args=[chat_id, warning_message_id]).start()
    else:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Telegram API error: {message_data}")

def delete_message(chat_id: int, message_id: int) -> None:
    """Delete a message from Telegram by message_id."""
    url = f'{TELEGRAM_API_BASE}/deleteMessage'
    payload = {'chat_id': chat_id, 'message_id': message_id}

    try:
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_message] Failed: {response.text}")
    except requests.RequestException as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_message] Exception: {e}")