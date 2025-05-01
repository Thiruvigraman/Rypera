#bot.py
import requests
from typing import Dict, Any
from config import BOT_TOKEN
from utils import log_to_discord, DISCORD_WEBHOOK_STATUS

def send_message(chat_id: int, text: str) -> None:
    """Send a message to a Telegram chat."""
    try:
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