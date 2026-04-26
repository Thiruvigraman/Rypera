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
    DISCORD_WEBHOOK_ERRORS,
)
from threading import Lock

FAILED_LOGS_LOCK = Lock()
MAX_FIELDS = 10
FAILED_LOGS: List[dict] = []
MAX_FAILED_LOGS = 5000
MAX_RETRY_PER_CYCLE = 100

session = requests.Session()



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

# ================= SAFETY =================

def validate_webhook_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://discord.com/api/webhooks/")

# ================= FALLBACK STORAGE =================

def write_fallback_log(entry):
    try:
        if os.path.exists("failed_logs.txt") and os.path.getsize("failed_logs.txt") > 5 * 1024 * 1024:
            os.remove("failed_logs.txt")  # reset

        with open("failed_logs.txt", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    except Exception:
        pass
# ================= ACCESS FORMAT =================

def build_access_text(entry):
    f = entry.get("fields", {})

    return (
        "📥 **ACCESS LOGS**\n\n"
        f">>> **File Accessed**\n\n"
        f"👤 User: {f.get('User')}\n"
        f"🆔 User ID: {f.get('User ID')}\n"
        f"🎬 Movie: {f.get('Movie')}"
    )


# ================= EMBED =================

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


# ================= SEND =================

def send_payload(url, payload):
    try:
        global_throttle()  

        res = session.post(
            url,
            json=payload,
            timeout=5,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; DiscordBot/1.0)"
            }
        )

        if res.status_code == 429:
            retry_after = res.json().get("retry_after", 1)
            time.sleep(retry_after)
            return False

        if res.status_code >= 400:
            print("DISCORD ERROR:", res.status_code)
            print(res.text[:200])  # shorter

        return res.status_code in (200, 204)

    except Exception as e:
        print("SEND ERROR:", str(e))
        return False

# ================= MAIN SENDER =================

def send_logs(log_type: str, entries: List[dict]):
    url = webhook_map.get(log_type) or webhook_map["status"]

    if not validate_webhook_url(url):
        for e in entries:
            add_failed(e)
            write_fallback_log(e)
        return False

    # ACCESS
    if log_type == "access":
        for entry in entries:
            msg = build_access_text(entry)

            if not send_payload(url, {"content": msg}):
                add_failed(entry)
                write_fallback_log(entry)

            time.sleep(0.05)  # ✅ throttle

        return True

    # ERROR routing
    is_error = any(e["severity"] == "error" for e in entries)

    if is_error:
        error_url = webhook_map.get("error")

        if validate_webhook_url(error_url):
            success = send_payload(error_url, build_embed(log_type, entries))

            time.sleep(0.1)  # ✅ throttle

            if not success:
                if not send_payload(webhook_map["status"], build_embed(log_type, entries)):
                    for e in entries:
                        add_failed(e)
                        write_fallback_log(e)

            return success

    # NORMAL
    success = send_payload(url, build_embed(log_type, entries))

    time.sleep(0.1)  # ✅ throttle

    if not success:
        for e in entries:
            add_failed(e)
            write_fallback_log(e)

    return success

# ================= RETRY =================

def retry_failed_logs():
    if not FAILED_LOGS:
        return

    with FAILED_LOGS_LOCK:
        current_logs = FAILED_LOGS[:MAX_RETRY_PER_CYCLE]
        remaining_logs = FAILED_LOGS[MAX_RETRY_PER_CYCLE:]

    retry_failed = []

    for entry in current_logs:
        log_type = entry.get("log_type", "status")
        url = webhook_map.get(log_type) or webhook_map["status"]

        if log_type == "access":
            msg = build_access_text(entry)
            success = send_payload(url, {"content": msg})
        else:
            success = send_payload(url, build_embed(log_type, [entry]))

        if not success:
            retry_failed.append(entry)

        time.sleep(0.1)  # ✅ FIXED (was dynamic spike)

    with FAILED_LOGS_LOCK:
        FAILED_LOGS.clear()
        FAILED_LOGS.extend(remaining_logs)
        FAILED_LOGS.extend(retry_failed)

# ================= HELPER =================

def add_failed(entry):
    with FAILED_LOGS_LOCK:
        if len(FAILED_LOGS) >= MAX_FAILED_LOGS:
            FAILED_LOGS.pop(0)
        FAILED_LOGS.append(entry)

# ================= WORKER =================

# ================= WORKER =================

def log_worker(stop_event=None):
    while True:
        if stop_event and stop_event.is_set():
            break

        interval = 3 if log_queue.qsize() > 100 else 5
        time.sleep(interval)

        grouped = {}

        while not log_queue.empty():
            try:
                entry = log_queue.get_nowait()
                grouped.setdefault(entry["log_type"], []).append(entry)
            except Exception:
                break

        retry_failed_logs()

        if not grouped:
            continue

        for log_type in ["error", "status", "list", "access"]:
            entries = grouped.get(log_type)
            if not entries:
                continue

            try:
                batch = entries[:20]
                remaining = entries[20:]

                send_logs(log_type, batch)

                for e in remaining:
                    log_queue.put(e)

            except Exception as e:
                print("Batch send error:", e)

        for _ in range(sum(len(v) for v in grouped.values())):
            log_queue.task_done()

# ================= MAIN LOG =================

def log_to_discord(message, log_type="status", severity="info", fields=None):
    try:
        entry = {
            "message": str(message),
            "severity": severity,
            "fields": fields or {},
            "timestamp": datetime.utcnow().isoformat(),
            "log_type": log_type,
        }

        if log_queue.qsize() > 10000:
            try:
                log_queue.get_nowait()
            except Exception:
                pass

        log_queue.put(entry)   # ✅ correct place
        return True

    except Exception as e:
        print("LOGGING FAILURE:", str(e))
        return False

# ================= GLOBAL THROTTLE =================

THROTTLE_LOCK = Lock()
LAST_SEND = 0

def global_throttle(min_interval=0.05):
    global LAST_SEND

    with THROTTLE_LOCK:
        now = time.time()
        diff = now - LAST_SEND

        if diff < min_interval:
            time.sleep(min_interval - diff)

        LAST_SEND = time.time()