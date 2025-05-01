#main.py
from flask import Flask
from config import DISCORD_WEBHOOK_STATUS
from webhook_handler import handle_webhook
from database import connect_db, close_db, process_scheduled_deletions
from utils import log_to_discord, flush_log_buffer
from threading import Thread
from time import sleep
from datetime import datetime, timedelta
import atexit
import sys
import traceback
import os
import signal

app = Flask(__name__)
LAST_DELETION_CHECK = None

try:
    connect_db()
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🚀 Bot is now online.", critical=True)
except Exception as e:
    error_message = f"❌ Startup failed: {str(e)}\n{traceback.format_exc()}"
    log_to_discord(DISCORD_WEBHOOK_STATUS, error_message, critical=True)
    print(error_message)
    sys.exit(1)

def on_exit():
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"⚠️ Bot is shutting down. Reason: Process terminated (PID: {os.getpid()})", critical=True)
    flush_log_buffer()
    close_db()

atexit.register(on_exit)

def handle_signal(signum, frame):
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"⚠️ Bot received signal {signum}. Shutting down.", critical=True)
    flush_log_buffer()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

def run_deletion_checker():
    global LAST_DELETION_CHECK
    while True:
        try:
            process_scheduled_deletions()
            LAST_DELETION_CHECK = datetime.utcnow()
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[deletion_checker] Error: {e}", critical=True)
        sleep(60)

def run_log_flusher():
    while True:
        try:
            flush_log_buffer()
        except Exception as e:
            print(f"[log_flusher] Error: {e}")
        sleep(300)

deletion_thread = Thread(target=run_deletion_checker, daemon=True)
deletion_thread.start()

log_thread = Thread(target=run_log_flusher, daemon=True)
log_thread.start()

@app.route("/webhook", methods=['POST'])
def webhook():
    return handle_webhook()

@app.route("/", methods=["GET"])
def home():
    try:
        from database import client
        client.admin.command('ping')
        return "Bot is running!", 200
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[health_check] Failed: {str(e)}", critical=True)
        return "Bot is unhealthy", 500

@app.route("/task-health", methods=["GET"])
def task_health():
    try:
        if LAST_DELETION_CHECK is None or (datetime.utcnow() - LAST_DELETION_CHECK) > timedelta(minutes=2):
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[task_health] Deletion task not running", critical=True)
            return "Deletion task is unhealthy", 500
        return "Deletion task is running!", 200
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[task_health] Failed: {e}", critical=True)
        return "Deletion task is unhealthy", 500

if __name__ == '__main__':
    import config
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)