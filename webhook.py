  #webhook.py

import requests
import time
from queue import Queue
from threading import Thread
import logging
from config import DISCORD_WEBHOOK_STATUS, EMBED_CONFIG, BETTERSTACK_ENDPOINT

logging.basicConfig(
    filename='/tmp/bot.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

log_queue = Queue()
last_log_time = 0
log_interval = 10

def log_to_discord(webhook, message, log_type='default', severity='info'):
    if severity == 'debug' and os.getenv('LOG_LEVEL', 'info') != 'debug':
        log_to_betterstack(f"{log_type}_{severity}", {"message": message, "webhook": webhook})
        return
    logging.log(
        getattr(logging, severity.upper(), logging.INFO),
        f"[{log_type}] {message}"
    )
    if severity not in ['warning', 'error'] and log_type != 'file_access':
        log_to_betterstack(f"{log_type}_{severity}", {"message": message, "webhook": webhook})
        return
    config = EMBED_CONFIG.get(log_type, EMBED_CONFIG['default'])
    embed = {
        'description': message[:4096],
        'color': config.get('color', 0x7289DA),
        'author': {'name': config.get('author', 'Telegram Bot')},
        'footer': {'text': config.get('footer', 'Powered by Rypera')},
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
    }
    if 'title' in config:
        embed['title'] = config['title']
    log_queue.put((webhook, embed, log_type, message, severity))

def process_log_queue():
    global last_log_time
    while True:
        webhook, embed, log_type, message, severity = log_queue.get()
        current_time = time.time()
        if log_type != 'file_access' and current_time - last_log_time < log_interval:
            time.sleep(log_interval - (current_time - last_log_time))
        for attempt in range(3):
            try:
                response = requests.post(webhook, json={'embeds': [embed]})
                last_log_time = current_time
                log_to_betterstack(f"{log_type}_log", {"webhook": webhook, "message": message, "status_code": response.status_code})
                if response.status_code != 204:
                    log_to_betterstack("discord_error", {"webhook": webhook, "status_code": response.status_code, "message": message})
                    if webhook != DISCORD_WEBHOOK_STATUS:
                        requests.post(DISCORD_WEBHOOK_STATUS, json={
                            'embeds': [{
                                'description': f"Failed to send Discord log to {webhook}: Status {response.status_code}",
                                'color': 0xFF0000,
                                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
                            }]
                        })
                break
            except Exception as e:
                if attempt == 2:
                    log_to_betterstack("discord_failure", {"webhook": webhook, "error": str(e), "message": message})
                    if webhook != DISCORD_WEBHOOK_STATUS:
                        requests.post(DISCORD_WEBHOOK_STATUS, json={
                            'embeds': [{
                                'description': f"Error sending Discord log to {webhook}: {str(e)}",
                                'color': 0xFF0000,
                                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
                            }]
                        })
                time.sleep(2)
        log_to_betterstack(f"{log_type}_{severity}", {"message": message, "webhook": webhook})
        log_queue.task_done()

Thread(target=process_log_queue, daemon=True).start()

def log_to_betterstack(event, data):
    try:
        requests.post(BETTERSTACK_ENDPOINT, json={
            'event': event,
            'data': data,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        })
    except Exception as e:
        logging.error(f"Error logging to BetterStack: {str(e)}")
        requests.post(DISCORD_WEBHOOK_STATUS, json={
            'embeds': [{
                'description': f"Error logging to BetterStack: {str(e)}",
                'color': 0xFF0000,
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
            }]
        })