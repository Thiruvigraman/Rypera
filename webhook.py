#webhook.py

import requests
import time
import queue
import threading
from config import DISCORD_WEBHOOK_STATUS, EMBED_CONFIG

# Queue for Discord logs
log_queue = queue.Queue()
shutdown_event = threading.Event()

def log_to_discord(webhook, message, log_type='default', severity='info'):
    # Add log to queue
    log_queue.put((webhook, message, log_type, severity))

def process_log_queue():
    while not shutdown_event.is_set():
        try:
            # Get log from queue with a timeout to check for shutdown
            webhook, message, log_type, severity = log_queue.get(timeout=1)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    config = EMBED_CONFIG.get(log_type, EMBED_CONFIG['default'])
                    default_config = EMBED_CONFIG['default']
                    formatted_message = message[:4096]  # Discord embed description limit
                    embed = {
                        'description': f"[{severity.upper()}] {formatted_message}",
                        'color': config.get('color', default_config.get('color', 0x7289DA)),
                        'author': {'name': config.get('author', default_config.get('author', 'Telegram Bot'))},
                        'footer': {'text': config.get('footer', default_config.get('footer', 'Powered by Rypera'))},
                        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
                    }
                    if 'title' in config:
                        embed['title'] = config['title']
                    response = requests.post(webhook, json={'embeds': [embed]})
                    if response.status_code == 429:  # Rate limit
                        retry_after = response.json().get('retry_after', 2) / 1000  # Convert ms to seconds
                        time.sleep(retry_after)
                        continue
                    response.raise_for_status()
                    break
                except Exception as e:
                    if attempt == max_retries - 1 and webhook != DISCORD_WEBHOOK_STATUS:
                        error_msg = f"Failed to send Discord log to {webhook} after {max_retries} attempts: {str(e)}"
                        log_queue.put((DISCORD_WEBHOOK_STATUS, error_msg, 'status', 'error'))
                    time.sleep(2)  # Delay between retries
            log_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            # Avoid infinite loop if queue processing fails
            log_queue.task_done()
            if not shutdown_event.is_set():
                log_queue.put((DISCORD_WEBHOOK_STATUS, f"Error in log queue processing: {str(e)}", 'status', 'error'))

# Start the log queue processor thread
log_processor_thread = threading.Thread(target=process_log_queue, daemon=True)
log_processor_thread.start()