#utils.py
import requests
import time
from typing import Dict
from datetime import datetime

# === Discord Webhook Logger ===
def log_to_discord(webhook: str, message: str) -> None:
    """Send logs to a Discord webhook as an embed with emojis and cool formatting."""
    if not webhook:
        return

    # Determine log type based on message content
    log_type = "info"
    color = 0x3498db  # Blue for info
    emoji = "ℹ️"

    if "error" in message.lower() or "failed" in message.lower() or "exception" in message.lower():
        log_type = "error"
        color = 0xe74c3c  # Red for errors
        emoji = "❌"
    elif "success" in message.lower() or "sent" in message.lower() or "added" in message.lower() or "connected" in message.lower():
        log_type = "success"
        color = 0x2ecc71  # Green for success
        emoji = "✅"
    elif "preview" in message.lower() or "cancelled" in message.lower() or "handling" in message.lower():
        log_type = "action"
        color = 0xf1c40f  # Yellow for actions
        emoji = "⚡"

    # Extract module (e.g., [send_message]) if present
    module = "General"
    if "[" in message and "]" in message:
        module = message.split("[")[1].split("]")[0]
        message_content = message.replace(f"[{module}]", "").strip()
    else:
        message_content = message

    # Create embed payload
    embed = {
        "title": f"{emoji} {log_type.capitalize()} Log",
        "description": f"**{message_content}**",
        "color": color,
        "fields": [
            {"name": "Module", "value": module, "inline": True},
            {"name": "Timestamp", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": True}
        ],
        "footer": {"text": "Telegram Bot by xAI | Powered by Grok"},
        "thumbnail": {
            "url": "https://i.imgur.com/8zX9j7Z.png"  # Optional: Add a cool bot logo or icon
        }
    }

    payload = {
        "embeds": [embed]
    }

    try:
        response = requests.post(webhook, json=payload, timeout=10)
        if not response.ok:
            print(f"[log_to_discord] Failed with status {response.status_code}: {response.text}")
    except requests.RequestException as e:
        print(f"[log_to_discord] Exception: {e}")

# === Simple Anti-Spam Cooldown ===
USER_COOLDOWNS: Dict[int, float] = {}

def is_spamming(user_id: int) -> bool:
    """Rate-limit user actions (5-second cooldown)."""
    now = time.time()
    last_action = USER_COOLDOWNS.get(user_id, 0)

    if now - last_action < 5:
        return True

    USER_COOLDOWNS[user_id] = now
    return False