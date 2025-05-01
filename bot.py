#bot.py
import requests
from typing import Dict, Any
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS
from utils import log_to_discord
import time
import threading

# Rate limiting
LAST_REQUEST_TIME = {}
REQUEST_LOCK = threading.Lock()

def rate_limit(chat_id: int, min_interval: float = 1.0) -> None:
    """Ensure minimum interval between requests to the same chat."""
    with REQUEST_LOCK:
        now = time.time()
        last_time = LAST_REQUEST_TIME.get(chat_id, 0)
        elapsed = now - last_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        LAST_REQUEST_TIME[chat_id] = time.time()

def send_message(chat_id: int, text: str) -> None:
    """Send a message to a Telegram chat."""
    try:
        rate_limit(chat_id)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Failed: {response.text}", critical=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message] Error: {str(e)}", critical=True)

def send_message_with_inline_keyboard(chat_id: int, text: str, keyboard: Dict[str, Any]) -> None:
    """Send a message with an inline keyboard."""
    try:
        rate_limit(chat_id)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message_with_inline_keyboard] Failed: {response.text}", critical=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[send_message_with_inline_keyboard] Error: {str(e)}", critical=True)