#config.py
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
APP_URL = os.getenv('APP_URL')

# Validate environment variables
required_vars = [
    'BOT_TOKEN', 'ADMIN_ID', 'BOT_USERNAME', 'MONGODB_URI',
    'DISCORD_WEBHOOK_STATUS', 'DISCORD_WEBHOOK_LIST_LOGS', 'DISCORD_WEBHOOK_FILE_ACCESS'
]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("ADMIN_ID must be a valid integer")