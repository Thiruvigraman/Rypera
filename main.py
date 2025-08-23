#main.py

import threading
import time
import os
import psutil
from webhook import log_to_discord
from config import DISCORD_WEBHOOK_STATUS
from handlers import start_polling

def resource_watchdog():
    """
    Monitors memory and CPU usage.
    Restarts if memory > 480MB (Render free tier safe limit).
    """
    process = psutil.Process()
    mem = process.memory_info().rss / 1024 / 1024  # MB
    cpu = process.cpu_percent(interval=0.2)

    if mem > 480:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Restarting bot due to high memory usage ({mem:.2f} MB)", log_type='status')
        os._exit(1)  # Render will restart automatically
    if cpu > 80:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"High CPU usage detected: {cpu:.2f}%", log_type='status')

def monitor_resources():
    while True:
        resource_watchdog()
        time.sleep(60)  # Check every 60 seconds

if __name__ == "__main__":
    # Start resource monitor thread
    threading.Thread(target=monitor_resources, daemon=True).start()

    # Start the bot
    log_to_discord(DISCORD_WEBHOOK_STATUS, "Bot starting...", log_type='startup')
    start_polling()