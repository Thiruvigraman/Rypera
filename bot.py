import requests
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id: str, text: str):
    url = f"{BASE_URL}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
    }
    response = requests.post(url, data=data)
    return response

def send_file(chat_id: str, file_id: str):
    url = f"{BASE_URL}/sendDocument"
    data = {
        'chat_id': chat_id,
        'document': file_id
    }
    response = requests.post(url, data=data)
    return response