# main.py

import atexit
import os
import signal
import time
import traceback
import psutil
import logging
from flask import Flask, request, jsonify
from telegram import cleanup_pending_files
from discord import log_to_discord
from config import DISCORD_WEBHOOK_STATUS, BOT_TOKEN, ADMIN_ID
from handlers import process_update

# Configure logging to Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.error(f"Health endpoint error: {e}\n{traceback.format_exc()}")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Health endpoint error: {e}\n{traceback.format_exc()}", log_type='status')
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    try:
        update = request.get_json()
        if update:
            logger.info(f"Received webhook update: {update}")
            process_update(update)
        return jsonify(success=True)
    except Exception as e:
        error_msg = f"Webhook error: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        log_to_discord(DISCORD_WEBHOOK_STATUS, error_msg, log_type='status')
        return jsonify({"error": str(e)}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    if request.json.get('admin_id') == str(ADMIN_ID):
        global is_shutting_down
        is_shutting_down = True
        logger.info("Shutdown initiated by admin")
        log_to_discord(DISCORD_WEBHOOK_STATUS, "Shutdown initiated by admin.", log_type='status')
        os._exit(0)
        return jsonify({"status": "Shutting down"})
    return jsonify({"error": "Unauthorized"}), 403

# On startup
logger.info(f"Bot starting (PID: {os.getpid()})")
log_to_discord(DISCORD_WEBHOOK_STATUS, f"Bot is now online! (PID: {os.getpid()})", log_type='status')
try:
    cleanup_pending_files()
except Exception as e:
    logger.error(f"Startup cleanup error: {e}\n{traceback.format_exc()}")
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"Startup cleanup error: {e}\n{traceback.format_exc()}", log_type='status')

# On exit
def on_exit():
    if is_shutting_down:
        logger.info(f"Bot offline (intentional shutdown, PID: {os.getpid()})")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Bot is now offline (intentional shutdown, PID: {os.getpid()}).", log_type='status')
    else:
        try:
            process = psutil.Process()
            mem = process.memory_info().rss / 1024 / 1024  # MB
            cpu = process.cpu_percent(interval=0.1)
            logger.error(f"Bot terminated unexpectedly (PID: {os.getpid()}, Memory: {mem:.2f} MB, CPU: {cpu:.2f}%)")
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Bot process terminated unexpectedly (PID: {os.getpid()}, Memory: {mem:.2f} MB, CPU: {cpu:.2f}%)", log_type='status')
        except:
            logger.error(f"Bot terminated unexpectedly (PID: {os.getpid()})")
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Bot process terminated unexpectedly (PID: {os.getpid()})", log_type='status')

def handle_shutdown(signum, frame):
    global is_shutting_down
    is_shutting_down = True
    logger.info(f"Received shutdown signal ({signum}, PID: {os.getpid()})")
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"Received shutdown signal ({signum}, PID: {os.getpid()}).", log_type='status')
    os._exit(0)

atexit.register(on_exit)
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), use_reloader=False)