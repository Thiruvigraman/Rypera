import requests
import os
from dotenv import load_dotenv
from discord_webhook import log_to_discord

# Load .env variables
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment.")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id: str, text: str):
    url = f"{BASE_URL}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        # Optionally, log the successful send to Discord
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Message sent to {chat_id}: {text}")
    except Exception as e:
        # Log error to Discord if sending message fails
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Failed to send message to {chat_id}: {e}")
        print(f"Failed to send message: {e}")
    return response

def send_file(chat_id: str, file_id: str):
    url = f"{BASE_URL}/sendDocument"
    data = {
        'chat_id': chat_id,
        'document': file_id
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        # Optionally, log the successful file send to Discord
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"File sent to {chat_id}: {file_id}")
    except Exception as e:
        # Log error to Discord if sending file fails
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Failed to send file to {chat_id}: {e}")
        print(f"Failed to send file: {e}")
    return response