          #utils.py
import requests
import time

# Webhook Logger
def log_to_discord(webhook, message):
    if webhook:
        try:
            requests.post(webhook, json={"content": message})
        except Exception as e:
            print(f"Failed to log to Discord: {e}")

# Anti-spam
USER_COOLDOWNS = {}
def is_spamming(user_id):
    now = time.time()
    last_time = USER_COOLDOWNS.get(user_id, 0)
    if now - last_time < 5:
        return True
    USER_COOLDOWNS[user_id] = now
    return False