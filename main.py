# file: main.py

import atexit
import os
import signal
import time
import requests
import psutil
import threading
from flask import Flask, request, jsonify
from utils import cleanup_pending_files
from webhook import log_to_discord,log_worker
from config import BOT_TOKEN, ADMIN_ID
from handlers import process_update
from globals import start_time,log_queue
from database import is_db_available
from database import setup_log_ttl
from concurrent.futures import ThreadPoolExecutor

EXECUTOR = ThreadPoolExecutor(max_workers=20)

app = Flask(__name__)

is_shutting_down = False
mongo_status_flag = True
initialized = False
init_lock = threading.Lock()

LAST_REQUEST_TIME = 0
log_stop_event = threading.Event()


# ================= AUTO WEBHOOK =================
def set_webhook():
    try:
        webhook_url = os.getenv("WEBHOOK_URL")

        if not webhook_url:
            log_to_discord("WEBHOOK_URL not set", "status", "error")
            return

        info = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo",
            timeout=10
        ).json()

        current_url = info.get("result", {}).get("url")

        if current_url == webhook_url:
            log_to_discord("Webhook already set", "status", "info")
            return

        res = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json={"url": webhook_url},
            timeout=10
        ).json()

        if res.get("ok"):
            log_to_discord(
                "Webhook set successfully",
                "status",
                "info",
                fields={"url": webhook_url}
            )
        else:
            log_to_discord(
                "Webhook setup failed",
                "status",
                "error",
                fields={"response": str(res)}
            )

    except Exception as e:
        log_to_discord(
            "Webhook setup error",
            "status",
            "error",
            fields={"error": str(e)}
        )


# ================= STARTUP CHECK =================
def startup_check():
    try:
        from database import db, movies_collection

        # Mongo
        if not is_db_available():
            mongo_status = "❌ Not Available"
        else:
            try:
                db.command("ping")
                mongo_status = "✅ Connected"
            except Exception as e:
                mongo_status = f"❌ Failed: {str(e)}"

        # Movies
        try:
            movie_count = movies_collection.count_documents({})
        except Exception:
            movie_count = "Error"

        # RAM
        process = psutil.Process()
        mem = process.memory_info().rss / 1024 / 1024

        # Webhook
        webhook_url = os.getenv("WEBHOOK_URL")

        try:
            info = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo",
                timeout=10
            ).json()

            current_url = info.get("result", {}).get("url")
            webhook_status = "✅ Active" if current_url == webhook_url else "⚠️ Mismatch"

        except Exception as e:
            webhook_status = f"❌ Error: {str(e)}"

        log_to_discord(
            "🚀 Bot Startup Report",
            "status",
            "info",
            fields={
                "🤖 Bot": "Started",
                "🗄 MongoDB": mongo_status,
                "🌐 Webhook": webhook_status,
                "🎬 Movies": movie_count,
                "🧠 RAM": f"{mem:.2f} MB",
                "⏱ Time": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            force_flush=True
        )

    except Exception as e:
        log_to_discord(
            "Startup check failed",
            "status",
            "error",
            fields={"error": str(e)}
        )


# ================= MONGO MONITOR =================
def monitor_mongo():
    global mongo_status_flag
    from database import db

    while True:
        try:
            if not is_db_available():
                raise Exception("DB not available")

            db.command("ping")

            if not mongo_status_flag:
                log_to_discord("MongoDB reconnected", "status", "info")
                mongo_status_flag = True

        except Exception as e:
            if mongo_status_flag:
                log_to_discord(
                    "MongoDB disconnected",
                    "status",
                    "error",
                    fields={"error": str(e)}
                )
                mongo_status_flag = False

        time.sleep(60)


def start_background_monitor():
    threading.Thread(target=monitor_mongo, daemon=True).start()




# ================= 🔥 INSTANT STARTUP =================
def init_system():
    global initialized

    with init_lock:
        if initialized:
            return
        initialized = True

    log_to_discord("🟢 Bot is online", "status", "info")
    
    from database import setup_log_ttl

    set_webhook()
    startup_check()
    start_background_monitor()
    cleanup_pending_files()

    setup_log_ttl()
    


threading.Thread(target=init_system, daemon=True).start()

threading.Thread(
    target=log_worker,
    args=(log_stop_event,),
    daemon=True
).start()

def start_cleanup_loop():
    while True:
        try:
            print("🧹 CLEANUP LOOP RUNNING")
            cleanup_pending_files()
        except Exception as e:
            print("Cleanup error:", e)

        time.sleep(15)  


threading.Thread(target=start_cleanup_loop, daemon=True).start()

# ================= ROUTES =================
@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200


@app.route("/health", methods=["GET"])
def health():
    try:
        process = psutil.Process()
        mem = process.memory_info().rss / 1024 / 1024
        cpu = process.cpu_percent(interval=0.1)

        uptime = time.time() - start_time
        days = int(uptime // 86400)
        hours = int((uptime % 86400) // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)

        return jsonify({
            "status": "healthy",
            "uptime_seconds": uptime,
            "uptime_readable": f"{days}d {hours}h {minutes}m {seconds}s",
            "memory_mb": mem,
            "cpu_percent": cpu
        })

    except Exception as e:
        log_to_discord(
            "Health endpoint error",
            "status",
            "error",
            fields={"error": str(e)}
        )
        return jsonify({"status": "error"}), 500


# ================= WEBHOOK =================
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def handle_webhook():
    global LAST_REQUEST_TIME

    try:
        now = time.time()
        if now - LAST_REQUEST_TIME < 0.02:
            return jsonify({"status": "rate_limited"}), 200

        LAST_REQUEST_TIME = now

        update = request.get_json(silent=True)

        if not isinstance(update, dict):
            return jsonify({"status": "ignored"}), 200

        # ✅ safe minimal logging (no spam)
        if "message" in update:
            user = update["message"].get("from", {})
            username = user.get("username") or user.get("first_name")

            pass

        # ✅ safe thread wrapper
        def safe_process(update):
            try:
                process_update(update)
            except Exception as e:
                log_to_discord(
                    "Thread crash",
                    "status",
                    "error",
                    fields={"error": str(e)}
                )

        EXECUTOR.submit(safe_process, update)

        return jsonify(success=True), 200

    except Exception as e:
        log_to_discord(
            "Webhook processing error",
            "status",
            "error",
            fields={"error": str(e)}
        )
        return jsonify({"error": str(e)}), 500

# ================= SHUTDOWN =================
@app.route("/shutdown", methods=["POST"])
def shutdown():
    if request.json.get("admin_id") == str(ADMIN_ID):
        global is_shutting_down
        is_shutting_down = True

        log_to_discord("Bot shutting down", "status", "warning")

        time.sleep(1)  # allow logs to flush
        os._exit(0)

    return jsonify({"error": "Unauthorized"}), 403


# ================= CLEAN EXIT =================
def on_exit():
    if is_shutting_down:
        log_to_discord("Bot stopped", "status", "info")


def handle_shutdown(signum, frame):
    global is_shutting_down
    is_shutting_down = True

    log_to_discord("Process terminated", "status", "warning")

    log_stop_event.set()
    log_queue.join()  # wait for logs to finish

    EXECUTOR.shutdown(wait=False)

    time.sleep(1)
    os._exit(0)


atexit.register(on_exit)
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


# ================= LOCAL RUN =================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        use_reloader=False
    )
