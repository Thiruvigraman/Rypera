# discord.py

import requests
import time
import logging
from config import DISCORD_WEBHOOK_STATUS, EMBED_CONFIG

# Configure logging to Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate-limiting state
last_log_times = {}  # Track last log time per webhook
log_interval = 2  # Seconds between logs per webhook (30 requests/min = ~2s/request)

def log_to_discord(webhook, message, log_type='default', max_retries=3):
    logger.info(f"Attempting to send Discord log to {webhook}: {message[:100]}... (type: {log_type})")
    if not webhook:
        logger.error(f"Webhook URL is empty or None for log type {log_type}")
        return
    if not webhook.startswith('https://discord.com/api/webhooks/'):
        logger.error(f"Invalid webhook URL format: {webhook}")
        return
    
    # Initialize last log time for this webhook
    if webhook not in last_log_times:
        last_log_times[webhook] = 0
    
    current_time = time.time()
    retries = 0
    
    while retries <= max_retries:
        # Check rate limit
        if current_time - last_log_times[webhook] < log_interval:
            time.sleep(log_interval - (current_time - last_log_times[webhook]))
            current_time = time.time()
        
        try:
            # Get embed config
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
            response.raise_for_status()  # Raise for bad status codes
            last_log_times[webhook] = current_time
            logger.info(f"Successfully sent Discord log to {webhook}: Status {response.status_code}")
            return
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retries += 1
                retry_after = e.response.json().get('retry_after', 1) / 1000  # Convert ms to seconds
                logger.warning(f"Rate limit hit for {webhook}, retrying after {retry_after}s (attempt {retries}/{max_retries})")
                time.sleep(retry_after)
                current_time = time.time()
            else:
                error_msg = f"Failed to send Discord log to {webhook}: {e}, Status: {e.response.status_code}"
                logger.error(error_msg)
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
                return
        except Exception as e:
            error_msg = f"Failed to send Discord log to {webhook}: {e}, Status: {response.status_code if 'response' in locals() else 'N/A'}"
            logger.error(error_msg)
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
            return
    logger.error(f"Max retries ({max_retries}) exceeded for {webhook}")