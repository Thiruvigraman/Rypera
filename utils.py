#utils.py

import requests
from typing import Dict, Any
from datetime import datetime, timedelta
import pytz
from config import (
    ADMIN_ID,
    DISCORD_WEBHOOK_STATUS,
    DISCORD_WEBHOOK_LIST_LOGS,
    DISCORD_WEBHOOK_FILE_ACCESS
)

# Store last message times for users to prevent spam
last_message_times: Dict[int, datetime] = {}
SPAM_THRESHOLD = 5  # seconds

# Log buffer for batching
LOG_BUFFER = []

# Webhook types configuration
WEBHOOK_TYPES: Dict[str, Dict[str, Any]] = {
    DISCORD_WEBHOOK_STATUS: {
        "type": "Bot Status",
        "emoji": "🌌",
        "color": 0xA100F2,  # Bright purple
        "critical_color": 0x7A00B8  # Darker purple
    },
    DISCORD_WEBHOOK_LIST_LOGS: {
        "type": "List Logs",
        "emoji": "📜",
        "color": 0x00FF85,  # Bright green
        "critical_color": 0x00B359  # Darker green
    },
    DISCORD_WEBHOOK_FILE_ACCESS: {
        "type": "File Access",
        "emoji": "📂",
        "color": 0xFF9500,  # Bright orange
        "critical_color": 0xCC7500  # Darker orange
    }
}

# Fallback for unknown webhooks
DEFAULT_WEBHOOK_TYPE = {
    "type": "Unknown Webhook",
    "emoji": "❓",
    "color": 0x808080,  # Gray
    "critical_color": 0x4B4B4B  # Darker gray
}

def log_to_discord(webhook_url: str, message: str, critical: bool = False, debug: bool = False) -> None:
    """Send log message to Discord webhook as a colorful embed."""
    LOG_BUFFER.append((webhook_url, message, critical, debug))
    if len(LOG_BUFFER) >= 10:  # Flush when buffer reaches 10 entries
        flush_log_buffer()

def flush_log_buffer() -> None:
    """Flush buffered logs to Discord."""
    for webhook_url, message, critical, debug in LOG_BUFFER:
        try:
            ist = pytz.timezone('Asia/Kolkata')
            timestamp = datetime.now(ist).isoformat()

            # Get webhook type or fallback
            webhook_config = WEBHOOK_TYPES.get(webhook_url, DEFAULT_WEBHOOK_TYPE)
            webhook_type = webhook_config["type"]
            emoji = webhook_config["emoji"]
            color = webhook_config["critical_color"] if critical else webhook_config["color"]

            # Extract context (e.g., function name) from message
            context = message.split(']')[0][1:] if message.startswith('[') else "General"

            # Create embed payload
            embed = {
                "title": f"{webhook_type} {emoji} {'⚠️' if critical else '🌟'}",
                "description": message,
                "color": color,
                "timestamp": timestamp,
                "fields": [
                    {
                        "name": "🔍 Severity",
                        "value": "🚨 Critical" if critical else "✅ Normal",
                        "inline": True
                    },
                    {
                        "name": "📋 Webhook",
                        "value": webhook_type,
                        "inline": True
                    },
                    {
                        "name": "🛠️ Context",
                        "value": context,
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Rypera",
                    "icon_url": "https://i.imgur.com/8j7k4fX.png"  # Replace with your bot's logo
                },
                "thumbnail": {
                    "url": "https://i.imgur.com/8j7k4fX.png"  # Replace with your bot's logo
                }
            }

            payload = {"embeds": [embed]}

            # Debug logging
            if debug:
                print(f"[log_to_discord] Sending to {webhook_url}: {payload}")

            response = requests.post(webhook_url, json=payload, timeout=5)
            if response.status_code not in (200, 204):
                print(f"[log_to_discord] Failed to send log to {webhook_url}: {response.status_code}, {response.text}")
                if debug:
                    print(f"[log_to_discord] Response: {response.text}")
        except requests.Timeout:
            print(f"[log_to_discord] Timeout sending log to {webhook_url}: Request timed out after 5 seconds")
        except Exception as e:
            print(f"[log_to_discord] Error sending log to {webhook_url}: {str(e)}")
    LOG_BUFFER.clear()

def is_spamming(user_id: int, admin_id: int) -> bool:
    """Check if user is sending messages too quickly."""
    if user_id == admin_id:
        return False
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    last_time = last_message_times.get(user_id)
    if last_time and (now - last_time).total_seconds() < SPAM_THRESHOLD:
        return True
    last_message_times[user_id] = now
    return False