# file: commands/health.py

import psutil
import time

from bot import send_message
from webhook import log_to_discord
from globals import start_time
from database import get_db_size_mb


def handle_health(chat_id, user):
    process = psutil.Process()

    mem = process.memory_info().rss / 1024 / 1024
    cpu = process.cpu_percent(interval=0.1)

    uptime = time.time() - start_time

    days = int(uptime // 86400)
    hours = int((uptime % 86400) // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)

    db_size = get_db_size_mb()

    msg = (
        f"🟢 Health Status\n\n"
        f"⏱ Uptime: {days}d {hours}h {minutes}m {seconds}s\n"
        f"🧠 RAM: {mem:.2f} MB\n"
        f"⚡ CPU: {cpu:.2f}%\n"
        f"🗄 MongoDB: {db_size} MB / 512 MB"
    )

    send_message(chat_id, msg)

    username = f"@{user['username']}" if user.get("username") else user.get("first_name", "Admin")

    log_to_discord(
        message="🟢 Health Checked",
        log_type="status",
        severity="info",
        fields={
            "admin": username,
            "uptime": f"{days}d {hours}h {minutes}m",
            "ram": f"{mem:.2f}MB",
            "cpu": f"{cpu:.2f}%",
            "db": f"{db_size}MB"
        }
    )