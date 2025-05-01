#utils.py
import requests
from typing import Optional
from datetime import datetime, timedelta
from config import MONGODB_URI
import pytz
import threading

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
    """Flush log buffer to Discord in batches."""
    with BUFFER_LOCK:
        if not LOG_BUFFER:
            return
        messages = LOG_BUFFER[:]
        LOG_BUFFER.clear()
    webhook_batches = {}
    for msg in messages:
        webhook_url = msg["webhook_url"]
        if webhook_url not in webhook_batches:
            webhook_batches[webhook_url] = []
        webhook_batches[webhook_url].append(msg["content"])
    for webhook_url, contents in webhook_batches.items():
        try:
            batch_message = "\n".join(contents)
            if len(batch_message) > 2000:
                batch_message = batch_message[:1997] + "..."
            response = requests.post(webhook_url, json={"content": batch_message}, timeout=10)
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