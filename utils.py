# utils.py
import requests
import time
from typing import Dict

# === Discord Webhook Logger ===
def log_to_discord(webhook: str, message: str) -> None:
    """Send logs to a Discord webhook."""
    if not webhook:
        return

    try:
        response = requests.post(webhook, json={"content": message}, timeout=10)
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