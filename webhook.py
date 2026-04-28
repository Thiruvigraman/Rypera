# file: webhook.py

import os
import requests
import time
import json
from globals import log_queue
from datetime import datetime
from typing import List
from config import (
    DISCORD_WEBHOOK_STATUS,
    DISCORD_WEBHOOK_LIST_LOGS,
    DISCORD_WEBHOOK_FILE_ACCESS,
    DISCORD_WEBHOOK_ERRORS,
)
from threading import Lock

# ================= GLOBALS =================

FAILED_LOGS_LOCK = Lock()
THROTTLE_LOCK = Lock()

FAILED_LOGS: List[dict] = []

MAX_FAILED_LOGS = 5000
MAX_RETRY_PER_CYCLE = 50
MAX_FIELDS = 10
FREEZE_REASON = None
LAST_SEND = 0
session = requests.Session()

# ================= GLOBAL LOG SWITCH =================

LOGGING_ENABLED = False
FREEZE_LOGS = False
FREEZE_UNTIL = 0
FREEZE_DURATION = 3600
ADMIN_ALERT_CHAT_ID = None

def set_logging(enabled: bool):
    global LOGGING_ENABLED
    LOGGING_ENABLED = enabled


def is_logging_enabled():
    return LOGGING_ENABLED


def get_log_queue_size():
    return log_queue.qsize()


def set_freeze(enabled: bool, duration: int = None, reason: str = None):
    global FREEZE_LOGS, FREEZE_UNTIL, FREEZE_REASON

    FREEZE_LOGS = enabled

    if enabled:
        FREEZE_UNTIL = time.time() + (duration or FREEZE_DURATION)
        FREEZE_REASON = reason or "Manual"
    else:
        FREEZE_UNTIL = 0
        FREEZE_REASON = None

def is_frozen():
    return FREEZE_LOGS

def check_auto_unfreeze():
    global FREEZE_LOGS, FREEZE_REASON, FREEZE_UNTIL

    if FREEZE_LOGS and FREEZE_UNTIL > 0:
        if time.time() >= FREEZE_UNTIL:
            print("🔥 AUTO UNFREEZE TRIGGERED")
            FREEZE_LOGS = False
            FREEZE_REASON = None
            FREEZE_UNTIL = 0

# ================= CONFIG =================

webhook_map = {
    "status": DISCORD_WEBHOOK_STATUS,
    "list": DISCORD_WEBHOOK_LIST_LOGS,
    "access": DISCORD_WEBHOOK_FILE_ACCESS,
    "error": DISCORD_WEBHOOK_ERRORS,
}

COLORS = {
    "info": 0x2ECC71,
    "warning": 0xF1C40F,
    "error": 0xE74C3C,
}

# ================= THROTTLE =================

def global_throttle(min_interval=0.2):
    global LAST_SEND
    with THROTTLE_LOCK:
        now = time.time()
        diff = now - LAST_SEND

        if diff < min_interval:
            time.sleep(min_interval - diff)

        LAST_SEND = time.time()

# ================= SAFETY =================

def validate_webhook_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://discord.com/api/webhooks/")

# ================= FALLBACK =================

def write_fallback_log(entry):
    try:
        if os.path.exists("failed_logs.txt") and os.path.getsize("failed_logs.txt") > 5 * 1024 * 1024:
            os.remove("failed_logs.txt")

        with open("failed_logs.txt", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

# ================= BUILDERS =================

def build_access_text(entry):
    f = entry.get("fields", {})
    return (
        "📥 **ACCESS LOGS**\n\n"
        f"👤 User: {f.get('User')}\n"
        f"🆔 User ID: {f.get('User ID')}\n"
        f"🎬 Movie: {f.get('Movie')}"
    )

def build_embed(log_type: str, entries: List[dict]):
    fields = []

    for entry in entries:
        value = "\n".join(
            [f"**{k}**: {v}" for k, v in entry.get("fields", {}).items()]
        )

        fields.append({
            "name": entry.get("message", "Log")[:256],
            "value": value[:1000] or "—",
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


# ================= CLEAR LOG QUEUE =================

def clear_all_logs():
    cleared_queue = 0

    # clear queue
    while not log_queue.empty():
        try:
            log_queue.get_nowait()
            cleared_queue += 1
        except Exception:
            break

    # clear failed logs
    with FAILED_LOGS_LOCK:
        failed_count = len(FAILED_LOGS)
        FAILED_LOGS.clear()

    return cleared_queue, failed_count

# ================= SEND =================


def send_payload(url, payload):
    return False

# ================= SEND LOGS =================


def send_logs(log_type: str, entries: List[dict]):
    if FREEZE_LOGS:
        return False

    url = webhook_map.get(log_type) or webhook_map["status"]

    if not validate_webhook_url(url):
        for e in entries:
            add_failed(e)
            write_fallback_log(e)
        return False

    if log_type == "access":
        for entry in entries:
            if not send_payload(url, {"content": build_access_text(entry)}):
                add_failed(entry)
                write_fallback_log(entry)
            time.sleep(0.1)
        return True

    if any(e["severity"] == "error" for e in entries):
        error_url = webhook_map.get("error")
        if validate_webhook_url(error_url):
            if send_payload(error_url, build_embed(log_type, entries)):
                return True

    success = send_payload(url, build_embed(log_type, entries))

    if not success:
        for e in entries:
            add_failed(e)
            write_fallback_log(e)

    return success

# ================= RETRY =================


def retry_failed_logs():
    return

# ================= FAILED =================

def add_failed(entry):
    with FAILED_LOGS_LOCK:
        entry["_retries"] = entry.get("_retries", 0) + 1

        if entry["_retries"] > 5:
            return

        if len(FAILED_LOGS) >= MAX_FAILED_LOGS:
            FAILED_LOGS.pop(0)

        FAILED_LOGS.append(entry)

# ================= WORKER =================

def log_worker(stop_event=None):
    while True:
        if stop_event and stop_event.is_set():
            break

        if not LOGGING_ENABLED:
            time.sleep(5)
            continue

        try:
            time.sleep(5)
        except Exception as e:
            print("Worker error:", str(e))

# ================= MAIN =================

def log_to_discord(message, log_type="status", severity="info", fields=None, force_flush=False):
    try:
        # 🚫 HARD STOP
        if not LOGGING_ENABLED:
            return False

        entry = {
            "message": str(message),
            "severity": severity,
            "fields": fields or {},
            "timestamp": datetime.utcnow().isoformat(),
            "log_type": log_type,
        }

        if force_flush:
            send_logs(log_type, [entry])
            return True

        if log_queue.qsize() > 10000:
            try:
                log_queue.get_nowait()
            except Exception:
                pass

        log_queue.put(entry)
        return True

    except Exception as e:
        print("LOGGING FAILURE:", str(e))
        return False