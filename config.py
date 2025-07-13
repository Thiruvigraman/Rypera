# config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
BOT_USERNAME = os.getenv('BOT_USERNAME')
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')
MONGODB_URI = os.getenv('MONGODB_URI')

# Validate required variables
if not BOT_TOKEN or not ADMIN_ID or not BOT_USERNAME or not MONGODB_URI:
    raise ValueError("Missing environment variables")

# Convert ADMIN_ID to integer
ADMIN_ID = int(ADMIN_ID)