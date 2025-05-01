#bot.py
import requests
import threading
from typing import Optional, Dict, Any
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS
from utils import log_to_discord

TELEGRAM_API_BASE = f'https://api.telegram.org/bot{BOT_TOKEN}'

def send_message(chat_id: int, text: str, parse_mode: Optional[str] = None, reply_markup: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send a Telegram message to the given chat_id with optional reply markup."""
    url = f'{TELEGRAM_API_BASE}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    if reply_markup:
        payload['reply_markup'] = reply_markup

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Telegram API error: {e}", critical=True)
        return {"ok": False, "error": str(e)}

def answer_callback_query(callback_query_id: str) -> None:
    """Answer a Telegram callback query to prevent timeouts."""
    url = f'{TELEGRAM_API_BASE}/answerCallbackQuery'
    payload = {'callback_query_id': callback_query_id}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[answer_callback_query] Error: {e}", critical=True)

def send_file(chat_id: int, file_id: str) -> None:
    """Send a Telegram document (file) by file_id and schedule deletion in 30 minutes."""
    from datetime import datetime, timedelta
    from database import schedule_deletion

    url = f'{TELEGRAM_API_BASE}/sendDocument'
    payload = {'chat_id': chat_id, 'document': file_id}

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        message_data = response.json()
    except requests.RequestException as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Error: {e}", critical=True)
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

        delete_at = datetime.utcnow() + timedelta(minutes=30)
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Scheduled deletion for message {file_message_id} at {delete_at}", critical=True)
        schedule_deletion(chat_id, file_message_id, delete_at)
        if warning_message_id:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Scheduled deletion for warning message {warning_message_id} at {delete_at}", critical=True)
            schedule_deletion(chat_id, warning_message_id, delete_at)
    else:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_file] Telegram API error: {message_data}", critical=True)

def delete_message(chat_id: int, message_id: int) -> bool:
    """Delete a message from Telegram by message_id. Returns True if successful."""
    if not chat_id or not message_id:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_message] Invalid chat_id or message_id", critical=True)
        return False

    url = f'{TELEGRAM_API_BASE}/deleteMessage'
    payload = {'chat_id': chat_id, 'message_id': message_id}

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            return True
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_message] Failed: {response.text}", critical=True)
        return False
    except requests.RequestException as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_message] Exception: {e}", critical=True)
        return False