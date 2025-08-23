#main.py

from flask import Flask, request
from handlers import process_update
from config import BOT_TOKEN, DISCORD_WEBHOOK_STATUS, PORT
from webhook import log_to_discord
import psutil
import os
import time
import threading
from utils import cleanup_old_messages

app = Flask(__name__)

def monitor_resources():
    while True:
        try:
            process = psutil.Process()
            mem = process.memory_info().rss / 1024 / 1024
            cpu = process.cpu_percent(interval=0.1)
            if mem > 480:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"Restarting due to high memory: {mem:.2f} MB", log_type='status', severity='warning')
                os._exit(1)  # Trigger Render auto-restart
            elif mem > 400 or cpu > 80:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"High resource usage: Memory {mem:.2f} MB, CPU {cpu:.2f}%", log_type='status', severity='warning')
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error monitoring resources: {str(e)}", log_type='status', severity='error')
        time.sleep(60)

threading.Thread(target=monitor_resources, daemon=True).start()
threading.Thread(target=cleanup_old_messages, daemon=True).start()

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        process_update(update)
        return "OK", 200
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error processing webhook: {str(e)}", log_type='status', severity='error')
        return "Error", 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        process = psutil.Process()
        mem = process.memory_info().rss / 1024 / 1024
        cpu = process.cpu_percent(interval=0.1)
        process_start_time = process.create_time()
        uptime = time.time() - process_start_time
        if uptime >= 86400:
            days = int(uptime // 86400)
            hours = int((uptime % 86400) // 3600)
            minutes = int((uptime % 3600) // 60)
            seconds = int(uptime % 60)
            uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        else:
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            seconds = int(uptime % 60)
            uptime_str = f"{hours}h {minutes}m {seconds}s"
        from database import db
        db_stats = db.command("dbStats")
        storage_used_mb = db_stats.get('dataSize', 0) / 1024 / 1024
        storage_total_mb = 512
        return (
            f"Bot Health Check\n\n"
            f"Uptime: {uptime_str}\n"
            f"Memory Usage: {mem:.2f} MB\n"
            f"CPU Usage: {cpu:.2f}%\n"
            f"MongoDB Storage Used: {storage_used_mb:.2f} MB\n"
            f"MongoDB Storage Total: {storage_total_mb:.2f} MB"
        ), 200
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Health check error: {str(e)}", log_type='status', severity='error')
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot is starting", log_type='status', severity='info')
    app.run(host='0.0.0.0', port=PORT)