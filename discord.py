# discord.py

import requests
import time
import logging  # Add for Render logging
from config import DISCORD_WEBHOOK_STATUS, EMBED_CONFIG

# Configure logging to Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_to_discord(webhook, message, log_type='default'):
    logger.info(f"Attempting to send Discord log to {webhook}: {message[:100]}... (type: {log_type})")
    if not webhook:
        logger.error(f"Webhook URL is empty or None for log type {log_type}")
        return
    try:
        # Validate webhook URL format
        if not webhook.startswith('https://discord.com/api/webhooks/'):
            logger.error(f"Invalid webhook URL format: {webhook}")
            return
        # Get embed config based on log type
        config = EMBED_CONFIG.get(log_type, EMBED_CONFIG['default'])
        default_config = EMBED_CONFIG['default']
        
        embed = {
            'description': message[:4096],  # Discord embed description limit
            'color': config.get('color', default_config.get('color', 0x7289DA)),
            'author': {'name': config.get('author', default_config.get('author', 'Telegram Bot'))},
            'footer': {'text': config.get('footer', default_config.get('footer', 'Powered by xAI'))},
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        }
        if 'title' in config:
            embed['title'] = config['title']
        
        response = requests.post(webhook, json={'embeds': [embed]}, timeout=5)
        response.raise_for_status()  # Raise exception for bad status codes
        logger.info(f"Successfully sent Discord log to {webhook}: Status {response.status_code}")
    except Exception as e:
        error_msg = f"Failed to send Discord log to {webhook}: {e}, Status: {response.status_code if 'response' in locals() else 'N/A'}"
        logger.error(error_msg)
        # Try fallback to DISCORD_WEBHOOK_STATUS if different
        if webhook != DISCORD_WEBHOOK_STATUS:
            try:
                requests.post(DISCORD_WEBHOOK_STATUS, json={
                    'embeds': [{
                        'description': error_msg[:4096],
                        'color': 0xFF0000,
                        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
                    }]
                }, timeout=5)
            except:
                logger.error("Failed to send fallback error log to DISCORD_WEBHOOK_STATUS")