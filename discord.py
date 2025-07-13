# discord.py

import requests
import time

last_log_time = 0
log_interval = 10  # Minimum seconds between logs

def log_to_discord(webhook, message):
    global last_log_time
    current_time = time.time()
    if webhook and (current_time - last_log_time >= log_interval):
        try:
            requests.post(webhook, json={"content": message[:2000]})
            last_log_time = current_time
        except:
            pass