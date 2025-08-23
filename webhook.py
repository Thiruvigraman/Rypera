#webhook.py

import requests
import threading
import queue
import time
from config import DISCORD_WEBHOOK_STATUS, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS

log_queue = queue.Queue()
shutdown_event = threading.Event()

# Validate webhook URLs
def validate_webhook_url(url, log_type):
    if not url:
        print(f"Debug: Webhook URL is empty for {log_type}")
        return False
    if not isinstance(url, str) or not url.startswith('https://discord.com/api/webhooks/'):
        print(f"Debug: Invalid webhook URL format for {log_type}: {url}")
        return False
    return True

# Log webhook URLs at startup
print(f"Debug: Initializing webhooks - STATUS: {DISCORD_WEBHOOK_STATUS}, LIST_LOGS: {DISCORD_WEBHOOK_LIST_LOGS}, FILE_ACCESS: {DISCORD_WEBHOOK_FILE_ACCESS}")
for url, log_type in [
    (DISCORD_WEBHOOK_STATUS, 'status'),
    (DISCORD_WEBHOOK_LIST_LOGS, 'list_logs'),
    (DISCORD_WEBHOOK_FILE_ACCESS, 'file_access')
]:
    validate_webhook_url(url, log_type)

def log_to_discord(webhook_url, message, log_type='status', severity='info'):
    if not validate_webhook_url(webhook_url, log_type):
        print(f"Debug: Skipping log due to invalid webhook URL for {log_type}: {message}")
        return
    payload = {
        "content": f"[{severity.upper()}] {message}",
        "username": f"Bot {log_type.capitalize()} Log",
    }
    log_queue.put((webhook_url, payload, message, log_type, severity))
    print(f"Debug: Queued log for {log_type}: {message}")

def process_log_queue():
    print("Debug: Starting log queue processor thread")
    while not shutdown_event.is_set():
        try:
            webhook_url, payload, message, log_type, severity = log_queue.get(timeout=1)
            print(f"Debug: Processing log for {log_type}: {message}")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(webhook_url, json=payload, timeout=10)
                    response.raise_for_status()
                    print(f"Debug: Successfully sent log to {webhook_url}: {message}")
                    break
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if e.response else 'Unknown'
                    error_detail = e.response.text if e.response else str(e)
                    print(f"Debug: HTTP error sending log to {webhook_url} (attempt {attempt + 1}/{max_retries}): Status {status_code}, Error: {error_detail}")
                    if status_code == 429:
                        retry_after = e.response.json().get('retry_after', 2000) / 1000
                        print(f"Debug: Rate limited for {webhook_url}, retrying after {retry_after}s")
                        time.sleep(retry_after)
                    elif attempt == max_retries - 1:
                        fallback_message = f"Failed to send {log_type} log after {max_retries} attempts: {message} (Status: {status_code}, Error: {error_detail})"
                        print(f"Debug: Queuing fallback log to STATUS: {fallback_message}")
                        if validate_webhook_url(DISCORD_WEBHOOK_STATUS, 'status'):
                            log_queue.put((DISCORD_WEBHOOK_STATUS, {
                                "content": f"[ERROR] {fallback_message}",
                                "username": "Bot Status Log"
                            }, fallback_message, 'status', 'error'))
                except requests.exceptions.RequestException as e:
                    print(f"Debug: Request error sending log to {webhook_url} (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt == max_retries - 1:
                        fallback_message = f"Failed to send {log_type} log after {max_retries} attempts: {message} (Error: {str(e)})"
                        print(f"Debug: Queuing fallback log to STATUS: {fallback_message}")
                        if validate_webhook_url(DISCORD_WEBHOOK_STATUS, 'status'):
                            log_queue.put((DISCORD_WEBHOOK_STATUS, {
                                "content": f"[ERROR] {fallback_message}",
                                "username": "Bot Status Log"
                            }, fallback_message, 'status', 'error'))
                except Exception as e:
                    print(f"Debug: Unexpected error sending log to {webhook_url} (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt == max_retries - 1:
                        fallback_message = f"Failed to send {log_type} log after {max_retries} attempts: {message} (Unexpected Error: {str(e)})"
                        print(f"Debug: Queuing fallback log to STATUS: {fallback_message}")
                        if validate_webhook_url(DISCORD_WEBHOOK_STATUS, 'status'):
                            log_queue.put((DISCORD_WEBHOOK_STATUS, {
                                "content": f"[ERROR] {fallback_message}",
                                "username": "Bot Status Log"
                            }, fallback_message, 'status', 'error'))
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Debug: Error in log queue processor: {str(e)}")
            if validate_webhook_url(DISCORD_WEBHOOK_STATUS, 'status'):
                log_queue.put((DISCORD_WEBHOOK_STATUS, {
                    "content": f"[ERROR] Log queue processing error: {str(e)}",
                    "username": "Bot Status Log"
                }, f"Log queue processing error: {str(e)}", 'status', 'error'))
    print("Debug: Log queue processor stopped due to shutdown")

def watchdog_queue_processor():
    print("Debug: Starting watchdog for log queue processor")
    while not shutdown_event.is_set():
        if not queue_thread.is_alive():
            print("Debug: Log queue processor thread is dead, restarting")
            global queue_thread
            queue_thread = threading.Thread(target=process_log_queue, daemon=True)
            queue_thread.start()
            print("Debug: Log queue processor thread restarted")
        time.sleep(5)
    print("Debug: Watchdog stopped due to shutdown")

# Start the queue processor and watchdog threads
queue_thread = threading.Thread(target=process_log_queue, daemon=True)
queue_thread.start()
print("Debug: Log queue processor thread started")
watchdog_thread = threading.Thread(target=watchdog_queue_processor, daemon=True)
watchdog_thread.start()
print("Debug: Watchdog thread started")