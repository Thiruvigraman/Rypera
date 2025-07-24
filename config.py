# config.py

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
BOT_USERNAME = os.getenv('BOT_USERNAME')
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')
MONGODB_URI = os.getenv('MONGODB_URI')
STORAGE_CHAT_ID = os.getenv('STORAGE_CHAT_ID')

if not all([BOT_TOKEN, ADMIN_ID, BOT_USERNAME, MONGODB_URI, STORAGE_CHAT_ID]):
    raise ValueError("Missing environment variables")

ADMIN_ID = int(ADMIN_ID)
STORAGE_CHAT_ID = int(STORAGE_CHAT_ID)


EMBED_CONFIG = {
    'default': {
        'color': 0x7289DA,  # Blurple fallback
        'author': 'Telegram Bot',
        'footer': 'Created by Thiru',
        'emoji': 'ℹ️'  
    },
    'status': {
        'color': 0xFF0000,  
        'title': 'Bot Status Update',
        'emoji': '🛑'  
    },
    'startup': {
        'color': 0x00FF00,  
        'title': 'Bot Startup',
        'emoji': '✅'  
    },
    'list_logs': {
        'color': 0x800080,
        'title': 'Admin Action Log',
        'emoji': '👑'  
    },
    'file_access': {
        'color': 0xFFFF00,
        'title': 'File Access Log',
        'emoji': '📂'  
    }
}