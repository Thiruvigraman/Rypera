# discord.py

import requests
import time
from config import EMBED_CONFIG

last_log_time = 0
log_interval = 10  # Minimum seconds between logs

def log_to_discord(webhook, message, log_type='default'):
    global last_log_time
    current_time = time.time()
    if webhook and (current_time - last_log_time >= log_interval):
        try:
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
                
            requests.post(webhook, json={'embeds': [embed]})
            last_log_time = current_time
        except Exception as e:
            # Silently fail to avoid crashing
            pass