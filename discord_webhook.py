 #discord_webhook.py

import os
import time
import requests
from ratelimit import limits, sleep_and_retry
from telegram import Update
from config import EMBED_CONFIG

CALLS = 30
RATE_LIMIT = 60

@sleep_and_retry
@limits(calls=CALLS, period=RATE_LIMIT)
def send_to_discord(webhook_url, embed):
    if not webhook_url:
        print(f"Webhook URL not set for {webhook_url}!")
        return
    payload = {"embeds": [embed]}
    headers = {"Content-Type": "application/json"}
    for attempt in range(3):
        try:
            response = requests.post(webhook_url, json=payload, headers=headers)
            response.raise_for_status()
            print(f"Sent to Discord: {embed['title']}")
            return
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                try:
                    retry_after = int(response.json().get('retry_after', 1000)) / 1000
                    print(f"Rate limited, retrying after {retry_after}s")
                    time.sleep(retry_after)
                except requests.exceptions.JSONDecodeError as json_err:
                    print(f"Failed to parse retry_after: {json_err}, response: {response.text}")
                    time.sleep(1)  # Fallback delay
            else:
                print(f"Failed to send to Discord: {e}, status: {response.status_code}, response: {response.text}")
                break
        except Exception as e:
            print(f"Error sending to Discord: {e}, response: {response.text if 'response' in locals() else 'No response'}")
            break

def log_to_discord(update: Update = None, message: str = None, log_type: str = 'status'):
    webhook_url = {
        'status': os.getenv('DISCORD_WEBHOOK_STATUS'),
        'list_logs': os.getenv('DISCORD_WEBHOOK_LIST_LOGS'),
        'file_access': os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')
    }.get(log_type, os.getenv('DISCORD_WEBHOOK_STATUS'))

    config = EMBED_CONFIG.get(log_type, EMBED_CONFIG['default'])
    embed = {
        "title": config.get('title', 'Bot Log'),
        "description": message,
        "color": config.get('color', 0x7289DA),
        "author": {"name": config.get('author', 'Telegram Bot')},
        "footer": {"text": config.get('footer', 'Powered by xAI')},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    }

    if update and log_type != 'status':
        username = update.effective_user.username or update.effective_user.full_name or str(update.effective_user.id)
        embed["description"] = f"[{username}]: {message}"

    send_to_discord(webhook_url, embed)