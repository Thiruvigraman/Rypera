#main.py

import atexit
import os
import signal
import time
import threading
import psutil
from flask import Flask, request, jsonify
from webhook import log_to_discord
from config import DISCORD_WEBHOOK_STATUS, BOT_TOKEN, ADMIN_ID

app = Flask(__name__)

start_time = time.time()
is_shutting_down = False

@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200

@app.route("/health", methods=["GET"])
def health():
    try:
        process = psutil.Process()
        mem = process.memory_info().rss / 1024 / 1024
        cpu = process.cpu_percent(interval=0.1)
        uptime = time.time() - start_time
        return jsonify({"status": "healthy", "uptime": uptime, "memory_mb": mem, "cpu_percent": cpu})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Health endpoint error: {str(e)}", log_type='status', severity='error')
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    try:
        update = request.get_json()
        if update:
            from handlers import process_update
            process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Webhook processing error: {str(e)}", log_type='status', severity='error')
        return jsonify({"error": str(e)}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    if request.json.get('admin_id') == str(ADMIN_ID):
        global is_shutting_down
        is_shutting_down = True
        log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot turned off", log_type='status', severity='info')
        os._exit(0)
        return jsonify({"status": "Shutting down"})
    return jsonify({"error": "Unauthorized"}), 403

def monitor_resources():
    while not is_shutting_down:
        process = psutil.Process()
        mem = process.memory_info().rss / 1024 / 1024
        cpu = process.cpu_percent(interval=0.1)
        if mem > 400 or cpu > 80:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"High resource usage: Memory {mem:.2f} MB, CPU {cpu:.2f}%", log_type='status', severity='warning')
        time.sleep(300)

threading.Thread(target=monitor_resources, daemon=True).start()

from utils import cleanup_pending_files
log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is online", log_type='startup', severity='info')
try:
    cleanup_pending_files()
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"Startup cleanup error: {str(e)}", log_type='status', severity='error')

def on_exit():
    if is_shutting_down:
        log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot turned off", log_type='status', severity='info')

def handle_shutdown(signum, frame):
    global is_shutting_down
    is_shutting_down = True
    log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot turned off", log_type='status', severity='info')
    os._exit(0)

atexit.register(on_exit)
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGQUIT, handle_shutdown)
signal.signal(signal.SIGHUP, handle_shutdown)

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), use_reloader=False)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Flask app crashed: {str(e)}", log_type='status', severity='error')
        raise