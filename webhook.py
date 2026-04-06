# file: webhook.py

import requests
import logging
import time
import json
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

# 🔥 LOG LEVEL CONTROL (ANTI-SPAM)
LOG_LEVELS = {
    "info": 1,
    "warning": 2,
    "error": 3,
}

CURRENT_LOG_LEVEL = 1  # 1=info, 2=warning, 3=error

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


# ================= FALLBACK =================
def write_fallback_log(entry):
    try:
        with open("failed_logs.txt", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except:
        pass


# ================= SAFETY =================
def validate_webhook_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://discord.com/api/webhooks/")


# ================= EMBED =================
def build_embed(log_type: str, entries: List[dict]):
    fields = []

    for entry in entries:
        try:
            value = "\n".join(
                [f"**{k}**: {v}" for k, v in entry.get("fields", {}).items()]
            )
        except Exception:
            value = "Invalid field data"

        fields.append({
            "name": entry.get("message", "Log"),
            "value": value or "—",
            "inline": False,
        })

    return {
        "embeds": [
            {
                "title": f"{log_type.upper()} LOGS",
                "color": COLORS.get(entries[-1].get("severity"), 0x95A5A6),
                "fields": fields[:MAX_FIELDS],
                "footer": {
                    "text": f"{len(entries)} events • {datetime.utcnow().strftime('%H:%M:%S UTC')}"
                },
            }
        ]
    }


# ================= SEND =================
def send_with_retry(url: str, payload: dict, log_type: str):
    delays = [1, 2, 4]

    for attempt in range(len(delays)):
        try:
            res = requests.post(url, json=payload, timeout=5)

            if res.status_code in (200, 204):
                return True

            if res.status_code == 429:
                retry_after = 2
                try:
                    retry_after = res.json().get("retry_after", 2)
                except:
                    pass

                time.sleep(retry_after)
                continue

        except Exception as e:
            logging.warning(f"{log_type} send error: {e}")

        time.sleep(delays[attempt])

    logging.error(f"{log_type} send failed permanently")
    return False


# ================= CHUNKS =================
def send_in_chunks(log_type: str, entries: List[dict]):
    url = webhook_map.get(log_type)

    if not validate_webhook_url(url):
        logging.error(f"{log_type} webhook invalid or missing")
        for e in entries:
            write_fallback_log(e)
        return

    for i in range(0, len(entries), MAX_FIELDS):
        chunk = entries[i:i + MAX_FIELDS]

        try:
            payload = build_embed(log_type, chunk)
            success = send_with_retry(url, payload, log_type)

            if not success:
                for e in chunk:
                    write_fallback_log(e)

        except Exception as e:
            logging.error(f"{log_type} chunk failed: {e}")

            for e in chunk:
                write_fallback_log(e)


# ================= FLUSH =================
def flush(log_type: str):
    try:
        buffer = log_buffers.get(log_type, [])

        if not buffer:
            return

        send_in_chunks(log_type, buffer)

        log_buffers[log_type] = []
        last_flush_time[log_type] = time.time()

    except Exception as e:
        logging.error(f"{log_type} flush error: {e}")


def flush_all():
    for log_type in list(log_buffers.keys()):
        flush(log_type)


# ================= MAIN LOG =================
def log_to_discord(
    message: str,
    log_type="status",
    severity="info",
    fields: Optional[Dict[str, str]] = None,
    force_flush: bool = False,
):
    try:
        # 🔥 LOG LEVEL FILTER
        if LOG_LEVELS.get(severity, 1) < CURRENT_LOG_LEVEL:
            return

        if log_type not in log_buffers:
            log_type = "status"

        entry = {
            "message": str(message),
            "severity": severity,
            "fields": fields or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # add source context
        entry["fields"]["source"] = log_type

        # 🔥 ERROR = instant send
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

    except Exception as e:
        print("LOGGING FAILURE:", str(e))