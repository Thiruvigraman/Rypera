# file : webhook.py

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
MAX_RETRY_PER_CYCLE = 30
MAX_FIELDS = 10
MAX_BATCH_SIZE = 5

LAST_SEND = 0
session = requests.Session()

# ================= LOG CONTROL =================

LOGGING_ENABLED = True
FREEZE_LOGS = False
FREEZE_UNTIL = 0
FREEZE_DURATION = 3600
ADMIN_ALERT_CHAT_ID = None


def set_logging(enabled: bool):
    global LOGGING_ENABLED
    LOGGING_ENABLED = enabled


def is_logging_enabled():
    return LOGGING_ENABLED


def set_freeze(enabled: bool, duration: int = None):
    global FREEZE_LOGS, FREEZE_UNTIL
    FREEZE_LOGS = enabled

    if enabled:
        FREEZE_UNTIL = time.time() + (duration or FREEZE_DURATION)
    else:
        FREEZE_UNTIL = 0


def check_auto_unfreeze():
    global FREEZE_LOGS
    if FREEZE_LOGS and FREEZE_UNTIL and time.time() >= FREEZE_UNTIL:
        print("🔥 AUTO UNFREEZE")
        FREEZE_LOGS = False


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

def global_throttle(min_interval=0.25):
    global LAST_SEND
    with THROTTLE_LOCK:
        now = time.time()
        diff = now - LAST_SEND

        if diff < min_interval:
            time.sleep(min_interval - diff)

        LAST_SEND = time.time()


# ================= UTIL =================

def validate_webhook_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://discord.com/api/webhooks/")


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
        f"👤 {f.get('User')}\n"
        f"🆔 {f.get('User ID')}\n"
        f"🎬 {f.get('Movie')}"
    )


def build_embed(log_type: str, entries: List[dict]):
    fields = []

    for entry in entries[:MAX_FIELDS]:
        value = "\n".join(
            [f"**{k}**: {v}" for k, v in entry.get("fields", {}).items()]
        )

        fields.append({
            "name": entry.get("message", "Log")[:256],
            "value": value[:1000] or "—",
            "inline": False,
        })

    return {
        "embeds": [{
            "title": f"{log_type.upper()} LOGS",
            "color": COLORS.get(entries[-1].get("severity"), 0x95A5A6),
            "fields": fields,
            "footer": {
                "text": f"{len(entries)} events • {datetime.utcnow().strftime('%H:%M:%S UTC')}"
            },
        }]
    }


# ================= FAILED =================

def add_failed(entry):
    with FAILED_LOGS_LOCK:
        entry["_retries"] = entry.get("_retries", 0) + 1

        if entry["_retries"] > 5:
            return

        if len(FAILED_LOGS) >= MAX_FAILED_LOGS:
            FAILED_LOGS.pop(0)

        FAILED_LOGS.append(entry)


def retry_failed_logs():
    if not FAILED_LOGS:
        return

    with FAILED_LOGS_LOCK:
        batch = FAILED_LOGS[:MAX_RETRY_PER_CYCLE]
        FAILED_LOGS[:] = FAILED_LOGS[MAX_RETRY_PER_CYCLE:]

    for entry in batch:
        url = webhook_map.get(entry.get("log_type"), webhook_map["status"])

        if entry.get("log_type") == "access":
            success = send_payload(url, {"content": build_access_text(entry)})
        else:
            success = send_payload(url, build_embed(entry["log_type"], [entry]))

        if not success:
            add_failed(entry)

        time.sleep(0.3)


# ================= SEND =================

def send_payload(url, payload):
    try:
        if not validate_webhook_url(url):
            return False

        global_throttle()

        res = session.post(url, json=payload, timeout=5)
        text = res.text.lower()

        # Cloudflare protection
        if "cloudflare" in text or "error 1015" in text:
            print("🚫 CLOUDFLARE → FREEZE")
            set_freeze(True)
            return False

        if res.status_code == 429:
            retry_after = res.json().get("retry_after", 2)
            time.sleep(max(2, retry_after))
            return False

        if res.status_code >= 400:
            return False

        return True

    except Exception:
        return False


def send_logs(log_type: str, entries: List[dict]):
    url = webhook_map.get(log_type) or webhook_map["status"]

    # Access logs = plain text
    if log_type == "access":
        for e in entries:
            if not send_payload(url, {"content": build_access_text(e)}):
                add_failed(e)
                write_fallback_log(e)
            time.sleep(0.1)
        return True

    # Error routing
    if any(e["severity"] == "error" for e in entries):
        error_url = webhook_map.get("error")
        if validate_webhook_url(error_url):
            send_payload(error_url, build_embed(log_type, entries))

    success = send_payload(url, build_embed(log_type, entries))

    if not success:
        for e in entries:
            add_failed(e)
            write_fallback_log(e)

    return success


# ================= WORKER =================

def log_worker(stop_event=None):
    last_retry = 0

    while True:
        if stop_event and stop_event.is_set():
            break

        check_auto_unfreeze()

        if FREEZE_LOGS:
            time.sleep(5)
            continue

        interval = 3 if log_queue.qsize() > 100 else 5
        time.sleep(interval)

        grouped = {}

        while True:
            try:
                entry = log_queue.get_nowait()
                grouped.setdefault(entry["log_type"], []).append(entry)
            except Exception:
                break

        # retry every 10 sec
        if time.time() - last_retry > 10:
            retry_failed_logs()
            last_retry = time.time()

        for log_type, entries in grouped.items():
            for i in range(0, len(entries), MAX_BATCH_SIZE):
                batch = entries[i:i + MAX_BATCH_SIZE]
                send_logs(log_type, batch)

        for _ in range(sum(len(v) for v in grouped.values())):
            log_queue.task_done()


# ================= MAIN =================

def log_to_discord(message, log_type="status", severity="info", fields=None, force_flush=False):
    if not LOGGING_ENABLED or FREEZE_LOGS:
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

    # queue protection
    if log_queue.qsize() > 10000:
        try:
            log_queue.get_nowait()
        except Exception:
            pass

    log_queue.put(entry)
    return True