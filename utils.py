#utils.py
import os
import requests
from typing import Optional
from datetime import datetime, timedelta
from config import MONGODB_URI
import pytz
import threading

DISCORD_WEBHOOK_STATUS = os.getenv("DISCORD_WEBHOOK_STATUS")
DISCORD_WEBHOOK_LIST_LOGS = os.getenv("DISCORD_WEBHOOK_LIST_LOGS")
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv("DISCORD_WEBHOOK_FILE_ACCESS")

LOG_BUFFER = []
BUFFER_LOCK = threading.Lock()
SPAM_TRACKER = {}

def log_to_discord(webhook_url: str, message: str, critical: bool = False) -> None:
    """Log message to Discord."""
    if MONGODB_URI in message:
        message = message.replace(MONGODB_URI, "[MONGODB_URI]")
    ist = pytz.timezone('Asia/Kolkata')
    timestamp = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S %Z")
    formatted_message = f"[{timestamp}] {message}"
    with BUFFER_LOCK:
        LOG_BUFFER.append({"content": formatted_message, "webhook_url": webhook_url, "critical": critical})
    if critical:
        flush_log_buffer()

def flush_log_buffer() -> None:
    """Flush log buffer to Discord."""
    with BUFFER_LOCK:
        if not LOG_BUFFER:
            return
        messages = LOG_BUFFER[:]
        LOG_BUFFER.clear()
    for msg in messages:
        try:
            response = requests.post(msg["webhook_url"], json={"content": msg["content"]}, timeout=10)
            if not response.ok:
                print(f"[flush_log_buffer] Failed to send to Discord: {response.text}")
        except Exception as e:
            print(f"[flush_log_buffer] Error: {str(e)}")

def is_spamming(user_id: int) -> bool:
    """Check if user is spamming."""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    if user_id not in SPAM_TRACKER:
        SPAM_TRACKER[user_id] = []
    SPAM_TRACKER[user_id] = [t for t in SPAM_TRACKER[user_id] if now - t < timedelta(seconds=10)]
    if len(SPAM_TRACKER[user_id]) >= 5:
        return True
    SPAM_TRACKER[user_id].append(now)
    return False