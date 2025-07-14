# telegram.py

import requests
import time
from config import BOT_TOKEN
import logging

# Configure logging to Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_message(chat_id, text, parse_mode=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f"Sent message to chat {chat_id}: {text[:50]}...")
    except Exception as e:
        logger.error(f"Failed to send message to chat {chat_id}: {e}")

def send_file(chat_id, file_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    payload = {
        "chat_id": chat_id,
        "document": file_id
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f"Sent file {file_id} to chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send file to chat {chat_id}: {e}")

def send_announcement(user_ids, message, parse_mode=None):
    success_count = 0
    failed_count = 0
    for user_id in user_ids:
        try:
            send_message(user_id, message, parse_mode)
            success_count += 1
            time.sleep(0.1)  # Avoid Telegram rate limits
        except Exception as e:
            logger.error(f"Failed to send announcement to user {user_id}: {e}")
            failed_count += 1
    return success_count, failed_count

def cleanup_pending_files():
    from database import db
    try:
        from discord import log_to_discord
        from config import DISCORD_WEBHOOK_STATUS
        result = db['pending_files'].delete_many({"timestamp": {"$lt": time.time() - 15 * 60}})
        if result.deleted_count:
            logger.info(f"Cleaned up {result.deleted_count} pending files")
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Cleaned up {result.deleted_count} pending files", log_type='status')
    except Exception as e:
        logger.error(f"Error cleaning up pending files: {e}")