#main.py
from flask import Flask, jsonify
from config import DISCORD_WEBHOOK_STATUS, APP_URL, BOT_TOKEN
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
import pytz
import requests

app = Flask(__name__)
LAST_DELETION_CHECK = None

def set_webhook():
    """Set Telegram webhook."""
    webhook_url = f"{APP_URL}/webhook"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    payload = {"url": webhook_url}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Webhook set to {webhook_url}")
        else:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Failed to set webhook: {response.text}", critical=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Webhook setup error: {str(e)}", critical=True)

try:
    connect_db()
    set_webhook()
    log_to_discord(DISCORD_WEBHOOK_STATUS, "🚀 Bot is now online.")
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

def keep_alive():
    """Ping /task-health every 5 minutes to prevent Render spin-down."""
    while True:
        try:
            response = requests.get(f"{APP_URL}/task-health", timeout=10)
            if response.status_code == 200:
                log_to_discord(DISCORD_WEBHOOK_STATUS, "[keep_alive] Service is awake.")
            else:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[keep_alive] Unexpected status: {response.status_code}", critical=True)
        except requests.RequestException as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[keep_alive] Error: {e}", critical=True)
        sleep(300)

def run_deletion_checker():
    """Run deletion checker every 60 seconds."""
    global LAST_DELETION_CHECK
    while True:
        try:
            process_scheduled_deletions()
            ist = pytz.timezone('Asia/Kolkata')
            LAST_DELETION_CHECK = datetime.now(ist)
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[deletion_checker] Error: {e}\n{traceback.format_exc()}", critical=True)
            sleep(10)
        sleep(60)

def run_log_flusher():
    """Flush log buffer every 5 minutes."""
    while True:
        try:
            flush_log_buffer()
        except Exception as e:
            print(f"[log_flusher] Error: {e}")
        sleep(300)

keep_alive_thread = Thread(target=keep_alive, daemon=True)
keep_alive_thread.start()

deletion_thread = Thread(target=run_deletion_checker, daemon=True)
deletion_thread.start()

log_thread = Thread(target=run_log_flusher, daemon=True)
log_thread.start()

@app.route("/webhook", methods=['POST'])
def webhook():
    return handle_webhook()

@app.route("/webhook/<path:invalid_path>", methods=['POST'])
def webhook_fallback(invalid_path):
    """Handle incorrect webhook URLs gracefully."""
    if not invalid_path.startswith('webhook'):
        return jsonify({"error": "Invalid endpoint"}), 404
    log_to_discord(
        DISCORD_WEBHOOK_STATUS,
        f"[webhook_fallback] Received request to invalid webhook path: /webhook/{invalid_path}",
        critical=True
    )
    return jsonify({"error": "Invalid webhook URL. Please check the Telegram webhook configuration."}), 404

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
        ist = pytz.timezone('Asia/Kolkata')
        if LAST_DELETION_CHECK is None or (datetime.now(ist) - LAST_DELETION_CHECK) > timedelta(minutes=2):
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[task_health] Deletion task not running", critical=True)
            return "Deletion task is unhealthy", 500
        from database import client
        client.admin.command('ping')
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=5)
        if not response.ok:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[task_health] Telegram API error: {response.text}", critical=True)
            return "Telegram API is unhealthy", 500
        return "All services are running!", 200
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[task_health] Failed: {e}", critical=True)
        return "Services are unhealthy", 500

if __name__ == '__main__':
    import config
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)