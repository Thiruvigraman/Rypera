# file: webhook.py

import requests
import logging
import time
from datetime import datetime
from typing import Dict, Optional, List
from config import (
    DISCORD_WEBHOOK_STATUS,
    DISCORD_WEBHOOK_LIST_LOGS,
    DISCORD_WEBHOOK_FILE_ACCESS,
)

BATCH_SIZE = 5
FLUSH_INTERVAL = 5
MAX_FIELDS = 25

COLORS = {
    "info": 0x2ECC71,
    "warning": 0xF1C40F,
    "error": 0xE74C3C,
}

log_buffers = {
    "status": [],
    "list": [],
    "access": [],
}

last_flush_time = {
    "status": time.time(),
    "list": time.time(),
    "access": time.time(),
}

webhook_map = {
    "status": DISCORD_WEBHOOK_STATUS,
    "list": DISCORD_WEBHOOK_LIST_LOGS,
    "access": DISCORD_WEBHOOK_FILE_ACCESS,
}


def validate_webhook_url(url: str) -> bool:
    return url and url.startswith("https://discord.com/api/webhooks/")


def build_embed(log_type: str, entries: List[dict]):
    fields = []

    for entry in entries:
        value = "\n".join(
            [f"**{k}**: {v}" for k, v in entry["fields"].items()]
        )

        fields.append({
            "name": entry["message"],
            "value": value or "—",
            "inline": False,
        })

    return {
        "embeds": [
            {
                "title": f"{log_type.upper()} LOGS",
                "color": COLORS.get(entries[-1]["severity"], 0x95A5A6),
                "fields": fields,
                "footer": {
                    "text": f"{len(entries)} events • {datetime.utcnow().strftime('%H:%M:%S UTC')}"
                },
            }
        ]
    }


def send_with_retry(url: str, payload: dict, log_type: str):
    delays = [1, 2, 4]

    for attempt in range(len(delays)):
        try:
            res = requests.post(url, json=payload, timeout=10)

            if res.status_code in (200, 204):
                return

            if res.status_code == 429:
                retry_after = res.json().get("retry_after", 2)
                time.sleep(retry_after)
                continue

        except Exception as e:
            logging.warning(f"{log_type} error: {e}")

        time.sleep(delays[attempt])

    logging.error(f"{log_type} send failed")


def send_in_chunks(log_type: str, entries: List[dict]):
    url = webhook_map.get(log_type)

    if not validate_webhook_url(url):
        logging.error(f"{log_type} webhook invalid")
        return

    for i in range(0, len(entries), MAX_FIELDS):
        chunk = entries[i:i + MAX_FIELDS]
        payload = build_embed(log_type, chunk)
        send_with_retry(url, payload, log_type)


def flush(log_type: str):
    buffer = log_buffers[log_type]
    if not buffer:
        return

    send_in_chunks(log_type, buffer)

    log_buffers[log_type] = []
    last_flush_time[log_type] = time.time()


def flush_all():
    for log_type in log_buffers:
        flush(log_type)


def log_to_discord(
    message: str,
    log_type="status",
    severity="info",
    fields: Optional[Dict[str, str]] = None,
    force_flush: bool = False,
):
    if log_type not in log_buffers:
        log_type = "status"

    entry = {
        "message": message,
        "severity": severity,
        "fields": fields or {},
    }

    # 🚨 ERROR = instant send
    if severity == "error":
        send_in_chunks(log_type, [entry])
        return

    log_buffers[log_type].append(entry)

    now = time.time()

    if len(log_buffers[log_type]) >= BATCH_SIZE:
        flush(log_type)
        return

    if now - last_flush_time[log_type] >= FLUSH_INTERVAL:
        flush(log_type)
        return

    if force_flush:
        flush(log_type)