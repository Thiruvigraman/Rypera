#main.py

import os
import time
import threading
import logging
import requests
from datetime import datetime
from fastapi import FastAPI, Request
from config import BOT_TOKEN, APP_URL, PORT, DISCORD_WEBHOOK_STATUS
from database import cleanup_overdue_deletions, process_scheduled_deletions, process_scheduled_message_deletions, close_connection
from utils import log_to_discord
from webhook_handler import handle_webhook_update

app = FastAPI()

# Global variable to track last deletion check
LAST_DELETION_CHECK = None

def run_deletion_checker():
    """Run the deletion checker in a separate thread."""
    global LAST_DELETION_CHECK
    log_to_discord(DISCORD_WEBHOOK_STATUS, "[deletion_checker] Thread started", critical=True)
    while True:
        try:
            deleted_count, remaining_count = process_scheduled_deletions()
            message_deleted_count = process_scheduled_message_deletions()
            LAST_DELETION_CHECK = datetime.utcnow()
            time.sleep(120)  # Check every 2 minutes
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[deletion_checker] Error: {str(e)}", critical=True)
            time.sleep(60)

def run_webhook_checker():
    """Periodically check and set the webhook."""
    while True:
        try:
            webhook_url = f"{APP_URL}/webhook"
            response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo").json()
            current_url = response.get('result', {}).get('url', '')
            if current_url != webhook_url:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                    json={"url": webhook_url}
                )
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[check_webhook] Webhook set to {webhook_url}")
            else:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[check_webhook] Webhook is correctly set")
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[check_webhook] Error: {str(e)}", critical=True)
        time.sleep(600)  # Check every 10 minutes

def keep_alive():
    """Keep the service awake by pinging task-health."""
    while True:
        try:
            response = requests.get(f"{APP_URL}/task-health", timeout=10)
            if response.ok:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[keep_alive] Service is awake.")
            else:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[keep_alive] Task health check failed: {response.status_code}", critical=True)
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[keep_alive] Error: {str(e)}", critical=True)
        time.sleep(600)  # Ping every 10 minutes

@app.on_event("startup")
async def startup_event():
    """Initialize the bot on startup."""
    try:
        cleanup_overdue_deletions()
        threading.Thread(target=run_deletion_checker, daemon=True).start()
        threading.Thread(target=run_webhook_checker, daemon=True).start()
        threading.Thread(target=keep_alive, daemon=True).start()
        log_to_discord(DISCORD_WEBHOOK_STATUS, "🚀 Bot is now online.")
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[main] Startup error: {str(e)}", critical=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Handle shutdown gracefully."""
    try:
        close_connection()
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"⚠️ Bot is shutting down. Reason: Process terminated (PID: {os.getpid()})", critical=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[main] Shutdown error: {str(e)}", critical=True)

@app.get("/task-health")
async def task_health():
    """Check the health of background tasks."""
    global LAST_DELETION_CHECK
    try:
        if LAST_DELETION_CHECK is None:
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[task_health] Unhealthy: Deletion task not started", critical=True)
            return {"status": "Unhealthy", "reason": "Deletion task not started"}, 500
        time_since_last_check = (datetime.utcnow() - LAST_DELETION_CHECK).total_seconds()
        if time_since_last_check > 300:  # 5 minutes
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[task_health] Unhealthy: Deletion task not running", critical=True)
            return {"status": "Unhealthy", "reason": "Deletion task not running"}, 500
        return {"status": "All services are running!"}, 200
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[task_health] Error: {str(e)}", critical=True)
        return {"status": "Unhealthy", "reason": str(e)}, 500

@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming Telegram webhook updates."""
    try:
        update = await request.json()
        handle_webhook_update(update)
        return {"status": "ok"}
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[webhook] Error: {str(e)}", critical=True)
        return {"status": "error"}, 500

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")