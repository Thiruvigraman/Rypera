#webhook.py

import requests
import time
from config import DISCORD_WEBHOOK_STATUS, EMBED_CONFIG

last_log_time = 0
log_interval = 10  # Minimum seconds between logs (except for file_access)

def log_to_discord(webhook, message, log_type='default'):
    global last_log_time
    current_time = time.time()
    # Skip delay for file_access logs to ensure immediate logging
    if log_type == 'file_access' or (webhook and (current_time - last_log_time >= log_interval)):
        try:
            config = EMBED_CONFIG.get(log_type, EMBED_CONFIG['default'])
            default_config = EMBED_CONFIG['default']

            # Prepend emoji to message
            emoji = config.get('emoji', default_config.get('emoji', 'ℹ️'))
            formatted_message = f"{emoji} {message[:4096]}"  # Discord embed description limit

            embed = {
                'description': formatted_message,
                'color': config.get('color', default_config.get('color', 0x7289DA)),
                'author': {'name': config.get('author', default_config.get('author', 'Telegram Bot'))},
                'footer': {'text': config.get('footer', default_config.get('footer', 'Powered by Rypera'))},
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
            }
            if 'title' in config:
                embed['title'] = config['title']

            response = requests.post(webhook, json={'embeds': [embed]})
            last_log_time = current_time
            if response.status_code != 204:
                error_msg = f"Failed to send Discord log to {webhook}: Status {response.status_code}"
                if webhook != DISCORD_WEBHOOK_STATUS:
                    requests.post(DISCORD_WEBHOOK_STATUS, json={
                        'embeds': [{
                            'description': f"🛑 {error_msg[:4096]}",
                            'color': 0xFF0000,
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
                        }]
                    })
        except Exception as e:
            error_msg = f"Error sending Discord log to {webhook}: {str(e)}"
            if webhook != DISCORD_WEBHOOK_STATUS:
                try:
                    requests.post(DISCORD_WEBHOOK_STATUS, json={
                        'embeds': [{
                            'description': f"🛑 {error_msg[:4096]}",
                            'color': 0xFF0000,
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
                        }]
                    })
                except:
                    pass  # Avoid infinite loop