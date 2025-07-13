# main.py

import atexit
import os
import signal
import time
import traceback
import psutil  # Add for resource monitoring
from flask import Flask, request, jsonify
from telegram import cleanup_pending_files
from discord import log_to_discord
from config import DISCORD_WEBHOOK_STATUS, BOT_TOKEN, ADMIN_ID
from handlers import process_update

app = Flask(__name__)

start_time = time.time()
is_shutting_down = False

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

@app.route("/health", methods=["GET"])
def health():
    try:
        # Get CPU and memory usage
        process = psutil.Process()
        mem = process.memory_info().rss / 1024 / 1024  # MB
        cpu = process.cpu_percent(interval=0.1)
        return jsonify({"status": "healthy", "uptime": time.time() - start_time, "memory_mb": mem, "cpu_percent": cpu})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Health check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def handle_webhook():
    try:
        update = request.get_json()
        if update:
            process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Webhook error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    if request.json.get('admin_id') == str(ADMIN_ID):
        global is_shutting_down
        is_shutting_down = True
        log_to_discord(DISCORD_WEBHOOK_STATUS, "Shutdown initiated by admin.")
        os._exit(0)
        return jsonify({"status": "Shutting down"})
    return jsonify({"error": "Unauthorized"}), 403

# On startup
log_to_discord(DISCORD_WEBHOOK_STATUS, f"Bot is now online! (PID: {os.getpid()})")
try:
    cleanup_pending_files()
except Exception as e:
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"Startup cleanup error: {e}\n{traceback.format_exc()}")

# On exit
def on_exit():
    if is_shutting_down:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Bot is now offline (intentional shutdown, PID: {os.getpid()}).")
    else:
        try:
            process = psutil.Process()
            mem = process.memory_info().rss / 1024 / 1024  # MB
            cpu = process.cpu_percent(interval=0.1)
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Bot process terminated unexpectedly (PID: {os.getpid()}, Memory: {mem:.2f} MB, CPU: {cpu:.2f}%)")
        except:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Bot process terminated unexpectedly (PID: {os.getpid()})")

def handle_shutdown(signum, frame):
    global is_shutting_down
    is_shutting_down = True
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"Received shutdown signal ({signum}, PID: {os.getpid()}).")
    os._exit(0)

atexit.register(on_exit)
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), use_reloader=False)