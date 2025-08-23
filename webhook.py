#webhook.py

import requests
import threading
import queue
import time
from config import DISCORD_WEBHOOK_STATUS, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS

log_queue = queue.Queue()
shutdown_event = threading.Event()

# Debug webhook URLs at startup
print(f"Debug: Initializing webhooks - STATUS: {DISCORD_WEBHOOK_STATUS}, LIST_LOGS: {DISCORD_WEBHOOK_LIST_LOGS}, FILE_ACCESS: {DISCORD_WEBHOOK_FILE_ACCESS}")

def log_to_discord(webhook_url, message, log_type='status', severity='info'):
    if not webhook_url:
        print(f"Debug: Webhook URL is empty for {log_type}, skipping log: {message}")
        return
    if not isinstance(webhook_url, str) or not webhook_url.startswith('https://discord.com/api/webhooks/'):
        print(f"Debug: Invalid webhook URL format for {log_type}: {webhook_url}")
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
                    if response.status_code == 429:
                        retry_after = response.json().get('retry_after', 2) / 1000  # Convert ms to seconds
                        print(f"Debug: Rate limited for {webhook_url}, retrying after {retry_after}s")
                        time.sleep(retry_after)
                    else:
                        print(f"Debug: HTTP error sending log to {webhook_url}: {str(e)}")
                        if attempt == max_retries - 1:
                            fallback_message = f"Failed to send {log_type} log after {max_retries} attempts: {message} (Error: {str(e)})"
                            print(f"Debug: Queuing fallback log to STATUS: {fallback_message}")
                            log_queue.put((DISCORD_WEBHOOK_STATUS, {
                                "content": f"[ERROR] {fallback_message}",
                                "username": "Bot Status Log"
                            }, fallback_message, 'status', 'error'))
                except requests.exceptions.RequestException as e:
                    print(f"Debug: Request error sending log to {webhook_url}: {str(e)}")
                    if attempt == max_retries - 1:
                        fallback_message = f"Failed to send {log_type} log after {max_retries} attempts: {message} (Error: {str(e)})"
                        print(f"Debug: Queuing fallback log to STATUS: {fallback_message}")
                        log_queue.put((DISCORD_WEBHOOK_STATUS, {
                            "content": f"[ERROR] {fallback_message}",
                            "username": "Bot Status Log"
                        }, fallback_message, 'status', 'error'))
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Debug: Error in log queue processor: {str(e)}")
            log_queue.put((DISCORD_WEBHOOK_STATUS, {
                "content": f"[ERROR] Log queue processing error: {str(e)}",
                "username": "Bot Status Log"
            }, f"Log queue processing error: {str(e)}", 'status', 'error'))
    print("Debug: Log queue processor stopped due to shutdown")

# Start the queue processor in a separate thread
queue_thread = threading.Thread(target=process_log_queue, daemon=True)
queue_thread.start()
print("Debug: Log queue processor thread started")