#utils.py
import requests
import time
from typing import Dict
from datetime import datetime
from config import MONGODB_URI
from threading import Lock
import pytz

LOG_BUFFER: Dict[str, str] = []
USER_COOLDOWNS: Dict[int, float] = {}
USER_COOLDOWNS_LOCK = Lock()

def log_to_discord(webhook: str, message: str, critical: bool = False) -> None:
    """Send logs to a Discord webhook, buffering non-critical logs."""
    if not critical:
        print(f"[LOG] {message}")
        return
    sanitized_message = message.replace(MONGODB_URI, "[REDACTED_MONGODB_URI]")
    LOG_BUFFER.append((webhook, sanitized_message))
    if len(LOG_BUFFER) >= 10:
        flush_log_buffer()

def flush_log_buffer() -> None:
    """Flush buffered logs to Discord webhooks with retries."""
    if not LOG_BUFFER:
        return
    grouped_logs = {}
    for webhook, message in LOG_BUFFER:
        if webhook not in grouped_logs:
            grouped_logs[webhook] = []
        grouped_logs[webhook].append(message)

    ist = pytz.timezone('Asia/Kolkata')
    for webhook, messages in grouped_logs.items():
        embed = {
            "title": "📜 Log Batch",
            "description": "\n".join(messages[:10]),
            "color": 0x3498db,
            "fields": [
                {"name": "Timestamp", "value": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST"), "inline": True}
            ],
            "footer": {"text": "Telegram Bot | Powered by rypera"},
            "thumbnail": {"url": "https://i.postimg.cc/wTWBBVLM/Screenshot-20240404-094145-Chrome.jpg"}
        }
        payload = {"embeds": [embed]}
        for attempt in range(3):
            try:
                response = requests.post(webhook, json=payload, timeout=10)
                if response.ok:
                    break
                print(f"[log_to_discord] Attempt {attempt + 1} failed: {response.text}")
            except requests.RequestException as e:
                print(f"[log_to_discord] Attempt {attempt + 1} exception: {e}")
            time.sleep(1)
    LOG_BUFFER.clear()

def is_valid_movie_name(name: str) -> bool:
    """Validate movie name (alphanumeric, spaces, underscores, hyphens)."""
    return bool(name and name.strip() and all(c.isalnum() or c in " _-" for c in name))

def is_spamming(user_id: int) -> bool:
    """Rate-limit user actions (5-second cooldown)."""
    with USER_COOLDOWNS_LOCK:
        now = time.time()
        last_action = USER_COOLDOWNS.get(user_id, 0)
        if now - last_action < 5:
            return True
        USER_COOLDOWNS[user_id] = now
        return False