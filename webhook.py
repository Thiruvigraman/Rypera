# file: webhook.py



import os
import requests
import logging
import time
import json
from globals import log_queue
from datetime import datetime
from typing import Dict, Optional, List
from config import (
    DISCORD_WEBHOOK_STATUS,
    DISCORD_WEBHOOK_LIST_LOGS,
    DISCORD_WEBHOOK_FILE_ACCESS,
)


MAX_FIELDS = 25
LAST_SEND_TIME = 0


# 🔥 LOG LEVEL CONTROL (ANTI-SPAM)
LOG_LEVELS = {
    "info": 1,
    "warning": 2,
    "error": 3,
}


LOG_LEVEL_MAP = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3
}

env_level = os.getenv("LOG_LEVEL", "INFO").upper()
CURRENT_LOG_LEVEL = LOG_LEVEL_MAP.get(env_level, 1)

COLORS = {
    "info": 0x2ECC71,
    "warning": 0xF1C40F,
    "error": 0xE74C3C,
}


webhook_map = {
    "status": DISCORD_WEBHOOK_STATUS,
    "list": DISCORD_WEBHOOK_LIST_LOGS,
    "access": DISCORD_WEBHOOK_FILE_ACCESS,
}

session = requests.Session()

# ================= FALLBACK =================

def write_fallback_log(entry):
    try:
        with open("failed_logs.txt", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ================= SAFETY =================

def validate_webhook_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://discord.com/api/webhooks/")


# ================= EMBED =================

MAX_VALUE_LENGTH = 900

def safe_truncate(text):
    return text[:MAX_VALUE_LENGTH] + "..." if len(text) > MAX_VALUE_LENGTH else text


def build_embed(log_type: str, entries: List[dict]):
    fields = []

    for entry in entries:
        try:
            raw = "\n".join(
                [f"{k}: {v}" for k, v in entry.get("fields", {}).items()]
            )
            value = safe_truncate(raw)
        except Exception:
            value = "Invalid field data"

        fields.append({
            "name": safe_truncate(entry.get("message", "Log"))[:256],
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

LAST_SEND_TIME = 0



def send_with_retry(url: str, payload: dict, log_type: str):
    delays = [3, 6, 10]

    for attempt in range(len(delays)):
        try:
            res = session.post(url, json=payload, timeout=5)

            print("DISCORD:", res.status_code, res.text)  # MUST be inside try

            if res.status_code in (200, 204):
                return True

            if res.status_code == 429:
                time.sleep(10)
                continue

        except Exception as e:
            print("SEND ERROR:", str(e))

        time.sleep(delays[attempt])

    logging.error(f"{log_type} send failed permanently")
    return False

# ================= CHUNKS =================

def send_in_chunks(log_type: str, entries: List[dict]) -> bool:
    url = webhook_map.get(log_type) or webhook_map.get("status")
    if not validate_webhook_url(url):
        logging.error(f"{log_type} webhook invalid or missing")
        for e in entries:
            write_fallback_log(e)
        return False

    success_all = True

    for i in range(0, len(entries), MAX_FIELDS):
        chunk = entries[i:i + MAX_FIELDS]

        try:
            payload = build_embed(log_type, chunk)
            success = send_with_retry(url, payload, log_type)

            if not success:
                success_all = False
                for e in chunk:
                    write_fallback_log(e)

        except Exception as e:
            success_all = False
            logging.error(f"{log_type} chunk failed: {e}")

            for e in chunk:
                write_fallback_log(e)

    return success_all




# ========== LOG WORKER==========

def log_worker(stop_event=None):
    BATCH_INTERVAL = 10  # seconds

    while True:
        if stop_event and stop_event.is_set():
            break

        time.sleep(BATCH_INTERVAL)

        grouped = {}

        # collect everything available (non-blocking)
        while not log_queue.empty():
            try:
                entry = log_queue.get_nowait()
                grouped.setdefault(entry["log_type"], []).append(entry)
            except Exception:
                break

        if not grouped:
            continue

        for log_type, entries in grouped.items():
            try:
                send_in_chunks(log_type, entries)
            except Exception as e:
                print("Batch send error:", e)

        # mark all done
        for _ in range(sum(len(v) for v in grouped.values())):
            log_queue.task_done()

# ================= MAIN LOG =================

def log_to_discord(
    message: str,
    log_type="status",
    severity="info",
    fields: Optional[Dict[str, str]] = None,
    force_flush: bool = False,
) -> bool:
    try:
        if LOG_LEVELS.get(severity, 1) < CURRENT_LOG_LEVEL:
            return True

        entry = {
            "message": str(message),
            "severity": severity,
            "fields": fields or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        entry["fields"]["source"] = log_type

        if log_queue.qsize() > 10000:
            try:
                log_queue.get_nowait()
            except Exception:
                pass

        log_queue.put({**entry, "log_type": log_type})
        return True

    except Exception as e:
        print("LOGGING FAILURE:", str(e))
        return False