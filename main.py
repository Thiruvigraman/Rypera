#main.py

try:
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
except Exception as e:
    error_message = f"❌ Import failed: {str(e)}\n{traceback.format_exc()}"
    print(error_message)
    try:
        from utils import log_to_discord
        from config import DISCORD_WEBHOOK_STATUS
        log_to_discord(DISCORD_WEBHOOK_STATUS, error_message, critical=True)
    except:
        pass
    sys.exit(1)

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

def check_webhook():
    """Verify and set Telegram webhook if necessary."""
    webhook_url = f"{APP_URL}/webhook"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    try:
        response = requests.get(url, timeout=10)
        if response.ok:
            webhook_info = response.json()['result']
            current_url = webhook_info.get('url', '')
            if current_url != webhook_url:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[check_webhook] Webhook mismatch: current={current_url}, expected={webhook_url}", critical=True)
                set_webhook()
            else:
                log_to_discord(DISCORD_WEBHOOK_STATUS, "[check_webhook] Webhook is correctly set")
        else:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[check_webhook] Failed to get webhook info: {response.text}", critical=True)
            set_webhook()
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[check_webhook] Error: {str(e)}", critical=True)
        set_webhook()

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
    """Ping /task-health every 10 minutes to prevent Render spin-down."""
    while True:
        try:
            response = requests.get(f"{APP_URL}/task-health", timeout=10)
            if response.status_code == 200:
                log_to_discord(DISCORD_WEBHOOK_STATUS, "[keep_alive] Service is awake.")
            else:
                log_to_discord(
                    DISCORD_WEBHOOK_STATUS,
                    f"[keep_alive] Unexpected status: {response.status_code}, Response: {response.text}",
                    critical=True
                )
        except requests.RequestException as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[keep_alive] Error: {e}", critical=True)
        sleep(600)  # Increased to 10 minutes

def run_deletion_checker():
    """Run deletion checker and log flusher every 120 seconds."""
    global LAST_DELETION_CHECK
    log_to_discord(DISCORD_WEBHOOK_STATUS, "[deletion_checker] Thread started", critical=True)
    while True:
        try:
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[deletion_checker] Running")
            process_scheduled_deletions()
            flush_log_buffer()  # Flush logs during deletion check
            ist = pytz.timezone('Asia/Kolkata')
            LAST_DELETION_CHECK = datetime.now(ist)
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[deletion_checker] Error: {e}\n{traceback.format_exc()}", critical=True)
            try:
                connect_db()
                log_to_discord(DISCORD_WEBHOOK_STATUS, "[deletion_checker] Reconnected to MongoDB")
            except Exception as e:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[deletion_checker] Reconnect failed: {e}", critical=True)
            sleep(10)
        sleep(120)  # Increased to 120 seconds to reduce CPU usage

def run_webhook_checker():
    """Periodically check webhook every 10 minutes."""
    while True:
        check_webhook()
        sleep(600)

keep_alive_thread = Thread(target=keep_alive, daemon=True)
keep_alive_thread.start()

deletion_thread = Thread(target=run_deletion_checker, daemon=True)
deletion_thread.start()

webhook_checker_thread = Thread(target=run_webhook_checker, daemon=True)
webhook_checker_thread.start()

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
        now = datetime.now(ist)
        deletion_status = "unknown"
        if LAST_DELETION_CHECK is None:
            deletion_status = "not running (LAST_DELETION_CHECK is None)"
        elif (now - LAST_DELETION_CHECK) > timedelta(minutes=3):
            deletion_status = f"stalled (last check: {(now - LAST_DELETION_CHECK).total_seconds()} seconds ago)"
        else:
            deletion_status = "running"

        from database import client
        mongo_status = "unknown"
        for attempt in range(3):
            try:
                client.admin.command('ping')
                mongo_status = "connected"
                break
            except Exception as e:
                if attempt == 2:
                    mongo_status = f"failed: {str(e)}"
                sleep(1)

        telegram_status = "unknown"
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=5)
        if response.ok:
            telegram_status = "connected"
        else:
            telegram_status = f"failed: {response.text}"

        webhook_status = "unknown"
        webhook_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=5)
        if webhook_info.ok and webhook_info.json()['result']['url'] == f"{APP_URL}/webhook":
            webhook_status = "configured"
        else:
            webhook_status = f"misconfigured: {webhook_info.text}"

        if deletion_status in ("not running", "stalled") or mongo_status != "connected" or telegram_status != "connected" or webhook_status != "configured":
            log_to_discord(
                DISCORD_WEBHOOK_STATUS,
                f"[task_health] Unhealthy: Deletion={deletion_status}, MongoDB={mongo_status}, Telegram={telegram_status}, Webhook={webhook_status}",
                critical=True
            )
            return f"Unhealthy: Deletion={deletion_status}, MongoDB={mongo_status}, Telegram={telegram_status}, Webhook={webhook_status}", 500

        return "All services are running!", 200
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[task_health] Unexpected error: {str(e)}\n{traceback.format_exc()}", critical=True)
        return "Services are unhealthy", 500

if __name__ == '__main__':
    try:
        import config
        port = int(os.getenv('PORT', 8443))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[main] Startup error: {str(e)}\n{traceback.format_exc()}", critical=True)
        raise