# config.py

import os
import logging

# Configure logging to Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
MONGODB_URI = os.getenv('MONGODB_URI')
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
BOT_USERNAME = os.getenv('BOT_USERNAME', '@YourBot')  # Default for safety
DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv('DISCORD_WEBHOOK_FILE_ACCESS')

# Validate environment variables
if not MONGODB_URI:
    logger.error("MONGODB_URI environment variable is missing")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is missing")
if not ADMIN_ID:
    logger.error("ADMIN_ID environment variable is missing")
else:
    try:
        ADMIN_ID = int(ADMIN_ID)  # Convert to integer
    except ValueError:
        logger.error("ADMIN_ID must be a valid integer")
        ADMIN_ID = None
if not DISCORD_WEBHOOK_STATUS:
    logger.error("DISCORD_WEBHOOK_STATUS environment variable is missing")
if not DISCORD_WEBHOOK_LIST_LOGS:
    logger.error("DISCORD_WEBHOOK_LIST_LOGS environment variable is missing")
if not DISCORD_WEBHOOK_FILE_ACCESS:
    logger.error("DISCORD_WEBHOOK_FILE_ACCESS environment variable is missing")

EMBED_CONFIG = {
    'default': {
        'color': 0x7289DA,  # Default blue
        'author': 'Telegram Bot',
        'footer': 'Powered by xAI'
    },
    'status': {
        'color': 0xFF0000,  # Red for startup/shutdown/errors
        'title': 'Bot Status Update'
    },
    'list_logs': {
        'color': 0x00FF00,  # Green for admin actions
        'title': 'Admin Action Log'
    },
    'file_access': {
        'color': 0x0000FF,  # Blue for file access
        'title': 'File Access Log'
    },
    'health': {
        'color': 0xFFFF00,  # Yellow for health checks
        'title': 'Health Check',
        'author': 'Bot Health Monitor',
        'footer': 'System Status'
    }
}