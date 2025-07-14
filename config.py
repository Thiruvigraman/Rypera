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

if not BOT_TOKEN or not ADMIN_ID or not BOT_USERNAME or not MONGODB_URI:
    raise ValueError("Missing environment variables")

ADMIN_ID = int(ADMIN_ID)

# Embed customization
EMBED_CONFIG = {
    'default': {
        'color': 0x7289DA,  # Default color (blurple)
        'author': 'Telegram Bot',
        'footer': 'Powered by xAI',
    },
    'status': {  # For DISCORD_WEBHOOK_STATUS
        'color': 0xFF0000,  # Red for status (e.g., errors, shutdowns)
        'title': 'Bot Status Update',
    },
    'list_logs': {  # For DISCORD_WEBHOOK_LIST_LOGS
        'color': 0x00FF00,  # Green for admin actions (e.g., movie added)
        'title': 'Admin Action Log',
    },
    'file_access': {  # For DISCORD_WEBHOOK_FILE_ACCESS
        'color': 0x0000FF,  # Blue for user file access
        'title': 'File Access Log',
    }
}