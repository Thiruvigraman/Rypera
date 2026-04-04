# file: main.py

import atexit
import os
import signal
import time
import requests
import psutil
from flask import Flask, request, jsonify
from bot import cleanup_pending_files
from webhook import log_to_discord
from config import BOT_TOKEN, ADMIN_ID

app = Flask(__name__)

start_time = time.time()
is_shutting_down = False


# ================= AUTO WEBHOOK =================
def set_webhook():
    try:
        webhook_url = os.getenv("WEBHOOK_URL")

        if not webhook_url:
            log_to_discord("WEBHOOK_URL not set", "status", "error")
            return

        # Check current webhook
        info = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo",
            timeout=10
        ).json()

        current_url = info.get("result", {}).get("url")

        if current_url == webhook_url:
            log_to_discord("Webhook already set", "status", "info")
            return

        # Set webhook
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


# ✅ Run on startup
set_webhook()
log_to_discord("Bot started", "status", "info")


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

        return jsonify({
            "status": "healthy",
            "uptime": time.time() - start_time,
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


# 🔥 IMPORTANT: matches your WEBHOOK_URL
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def handle_webhook():
    try:
        update = request.get_json()

        if update:
            from handlers import process_update
            process_update(update)

        return jsonify(success=True)

    except Exception as e:
        log_to_discord(
            "Webhook processing error",
            "status",
            "error",
            fields={"error": str(e)}
        )
        return jsonify({"error": str(e)}), 500


@app.route("/shutdown", methods=["POST"])
def shutdown():
    if request.json.get("admin_id") == str(ADMIN_ID):
        global is_shutting_down
        is_shutting_down = True

        log_to_discord("Bot shutting down", "status", "warning")

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

    os._exit(0)


atexit.register(on_exit)
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


# ================= START =================
if __name__ == "__main__":
    try:
        cleanup_pending_files()

        app.run(
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8080)),
            use_reloader=False
        )

    except Exception as e:
        log_to_discord(
            "Flask crash",
            "status",
            "error",
            fields={"error": str(e)}
        )
        raise