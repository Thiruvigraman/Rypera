#discord_webhook.py

import os
import requests
from ratelimit import limits, sleep_and_retry
from telegram import Update  # Correct import from python-telegram-bot

# Discord webhook URLs from environment variables
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')

CALLS = 30
RATE_LIMIT = 60

@sleep_and_retry
@limits(calls=CALLS, period=RATE_LIMIT)
def send_to_discord(webhook_url, message):
    if not webhook_url:
        print(f"Webhook URL not set for {webhook_url}!")
        return
    payload = {"content": message}
    headers = {"Content-Type": "application/json"}
    for attempt in range(3):
        try:
            response = requests.post(webhook_url, json=payload, headers=headers)
            response.raise_for_status()
            print(f"Sent to Discord: {message}")
            return
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                retry_after = int(response.json().get('retry_after', 1000)) / 1000
                print(f"Rate limited, retrying after {retry_after}s")
                time.sleep(retry_after)
            else:
                print(f"Failed to send to Discord: {e}")
                break
        except Exception as e:
            print(f"Error sending to Discord: {e}")
            break

def log_to_discord(update: Update = None, message: str = None, log_type: str = 'status'):
    if update:  # Handle cases where update is provided (e.g., for commands)
        username = update.effective_user.username or update.effective_user.full_name or str(update.effective_user.id)
        formatted_message = f"[{username}]: {message}"
    else:  # Handle cases without update (e.g., cleanup errors)
        formatted_message = message
    webhook_url = {
        'status': DISCORD_WEBHOOK_STATUS,
        'list': DISCORD_WEBHOOK_LIST_LOGS,
        'file': DISCORD_WEBHOOK_FILE_ACCESS
    }.get(log_type, DISCORD_WEBHOOK_STATUS)
    send_to_discord(webhook_url, formatted_message)