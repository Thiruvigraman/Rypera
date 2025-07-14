# main.py

import atexit
import os
import signal
import time
import traceback
import psutil
from flask import Flask, request, jsonify
from telegram_bot import cleanup_pending_files
from discord import log_to_discord
from config import DISCORD_WEBHOOK_STATUS, BOT_TOKEN, ADMIN_ID
from handlers import process_update

app = Flask(__name__)

start_time = time.time()  # Global start_time for /health endpoint
is_shutting_down = False

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

@app.route("/health", methods=["GET"])
def health():
    try:
        process = psutil.Process()
        mem = process.memory_info().rss / 1024 / 1024  # MB
        cpu = process.cpu_percent(interval=0.1)
        return jsonify({"status": "healthy", "uptime": time.time() - start_time, "memory_mb": mem, "cpu_percent": cpu})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Attempting to log health endpoint error: {e}\n{traceback.format_exc()}", log_type='status')
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    try:
        update = request.get_json()
        if update:
            process_update(update)
        return jsonify(success=True)
    except Exception as e:
        error_msg = f"Webhook error: {e}\n{traceback.format_exc()}"
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Attempting to log webhook error: {error_msg}", log_type='status')
        return jsonify({"error": str(e)}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    if request.json.get('admin_id') == str(ADMIN_ID):
        global is_shutting_down
        is_shutting_down = True
        log_to_discord(DISCORD_WEBHOOK_STATUS, "Attempting to log shutdown initiated by admin.", log_type='status')
        os._exit(0)
        return jsonify({"status": "Shutting down"})
    return jsonify({"error": "Unauthorized"}), 403

# On startup
log_to_discord(DISCORD_WEBHOOK_STATUS, f"Attempting to log: Bot is now online! (PID: {os.getpid()})", log_type='status')
try:
    cleanup_pending_files()
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"Attempting to log startup cleanup error: {e}\n{traceback.format_exc()}", log_type='status')

# On exit
def on_exit():
    if is_shutting_down:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Attempting to log: Bot is now offline (intentional shutdown, PID: {os.getpid()}).", log_type='status')
    else:
        try:
            process = psutil.Process()
            mem = process.memory_info().rss / 1024 / 1024  # MB
            cpu = process.cpu_percent(interval=0.1)
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Attempting to log: Bot process terminated unexpectedly (PID: {os.getpid()}, Memory: {mem:.2f} MB, CPU: {cpu:.2f}%)", log_type='status')
        except:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Attempting to log: Bot process terminated unexpectedly (PID: {os.getpid()})", log_type='status')

def handle_shutdown(signum, frame):
    global is_shutting_down
    is_shutting_down = True
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"Attempting to log: Received shutdown signal ({signum}, PID: {os.getpid()}).", log_type='status')
    os._exit(0)

atexit.register(on_exit)
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), use_reloader=False)