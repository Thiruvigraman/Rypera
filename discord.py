import requests

import time
from ratelimit import limits, sleep_and_retry
from telegram import Update

# Discord webhook URLs (loaded from environment variables)
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')

# Rate limit: 30 calls per minute (Discord's limit)
CALLS = 30
RATE_LIMIT = 60

@sleep_and_retry
@limits(calls=CALLS, period=RATE_LIMIT)
def send_to_discord(webhook_url, message):
    """Send a message to a Discord webhook with rate limiting and retries."""
    if not webhook_url:
        print("Webhook URL not set!")
        return

    payload = {"content": message}
    headers = {"Content-Type": "application/json"}

    for attempt in range(3):  # Retry up to 3 times
        try:
            response = requests.post(webhook_url, json=payload, headers=headers)
            response.raise_for_status()  # Raise exception for bad status codes
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

def log_status(update: Update, message: str):
    """Log status messages with username."""
    username = update.effective_user.username or update.effective_user.full_name or str(update.effective_user.id)
    formatted_message = f"[{username}]: {message}"
    send_to_discord(DISCORD_WEBHOOK_STATUS, formatted_message)

def log_file_access(update: Update, file_name: str):
    """Log file access with username."""
    username = update.effective_user.username or update.effective_user.full_name or str(update.effective_user.id)
    formatted_message = f"[{username}] accessed file: {file_name}"
    send_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, formatted_message)

def log_list_command(update: Update, command: str):
    """Log list command with username."""
    username = update.effective_user.username or update.effective_user.full_name or str(update.effective_user.id)
    formatted_message = f"[{username}] used command: {command}"
    send_to_discord(DISCORD_WEBHOOK_LIST_LOGS, formatted_message)