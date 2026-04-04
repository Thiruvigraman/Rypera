# file: handlers.py

from config import ADMIN_ID, BOT_TOKEN
from database import (
    load_movies, save_movie, delete_movie,
    add_user, get_stats, rename_movie, get_all_users
)
from bot import send_message, send_file
from webhook import log_to_discord
import time
import psutil
import requests
from globals import start_time

TEMP_FILE_IDS = {}
PENDING_ANNOUNCEMENT = {}


def get_user_display_name(user):
    return f"@{user['username']}" if user.get('username') else user.get('first_name', 'User')


def safe_send(chat_id, text):
    result = send_message(chat_id, text)
    if not result or not result.get("ok"):
        log_to_discord("Telegram send failed", "status", "error")


def process_update(update):
    try:
        # ================= BUTTON HANDLER =================
        if "callback_query" in update:
            query = update["callback_query"]
            data = query.get("data")
            user_id = query["from"]["id"]
            chat_id = query["message"]["chat"]["id"]

            # remove loading
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                json={"callback_query_id": query["id"]}
            )

            # ===== CONFIRM =====
            if data == "announce_confirm" and user_id == ADMIN_ID:
                announcement = PENDING_ANNOUNCEMENT.get(user_id)

                if not announcement:
                    safe_send(chat_id, "No pending announcement")
                    return

                users = get_all_users()
                success, failed = 0, 0

                for u in users:
                    result = send_message(u['user_id'], announcement)

                    if result and result.get("ok"):
                        success += 1
                    else:
                        failed += 1

                    time.sleep(0.1)

                PENDING_ANNOUNCEMENT.pop(user_id, None)

                # Telegram summary
                safe_send(
                    chat_id,
                    f"✅ Announcement sent\n\nSuccess: {success}\nFailed: {failed}"
                )

                # ✅ Discord summary (FIXED)
                log_to_discord(
                    "📢 Announcement Sent",
                    "list",
                    "info",
                    fields={
                        "Success": success,
                        "Failed": failed,
                        "Total Users": success + failed
                    }
                )

                return

            # ===== CANCEL =====
            if data == "announce_cancel" and user_id == ADMIN_ID:
                PENDING_ANNOUNCEMENT.pop(user_id, None)
                safe_send(chat_id, "❌ Announcement cancelled")

                log_to_discord(
                    "Announcement cancelled",
                    "list",
                    "warning"
                )
                return

        # ================= MESSAGE =================
        if 'message' not in update:
            return

        message = update['message']
        chat_id = message['chat']['id']
        user = message['from']
        user_id = user['id']
        text = message.get('text', '')
        document = message.get('document')
        video = message.get('video')

        display_name = get_user_display_name(user)

        if user_id != ADMIN_ID:
            add_user(user_id, display_name)

        # ===== ANNOUNCE =====
        if text.startswith('/announce') and user_id == ADMIN_ID:
            parts = text.split(maxsplit=1)

            if len(parts) < 2:
                safe_send(chat_id, "Usage: /announce message")
                return

            announcement = parts[1]
            PENDING_ANNOUNCEMENT[user_id] = announcement

            keyboard = {
                "inline_keyboard": [[
                    {"text": "✅ Confirm", "callback_data": "announce_confirm"},
                    {"text": "❌ Cancel", "callback_data": "announce_cancel"}
                ]]
            }

            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"📢 Preview:\n\n{announcement}",
                    "reply_markup": keyboard
                }
            )

            log_to_discord(
                "Announcement preview created",
                "list",
                "info"
            )
            return

        # ===== UPLOAD =====
        if (document or video) and user_id == ADMIN_ID:
            file_id = document['file_id'] if document else video['file_id']
            TEMP_FILE_IDS[chat_id] = file_id

            safe_send(chat_id, "Send movie name")
            log_to_discord("File uploaded", "list", "info")
            return

        # ===== SAVE =====
        if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
            save_movie(text, TEMP_FILE_IDS[chat_id])
            TEMP_FILE_IDS.pop(chat_id)

            safe_send(chat_id, f"Movie '{text}' added")
            log_to_discord("Movie added", "list", "info")
            return

        # ===== RENAME =====
        if text.startswith('/rename_file') and user_id == ADMIN_ID:
            parts = text.split(maxsplit=2)

            if len(parts) < 3:
                safe_send(chat_id, "Usage: /rename_file old new")
                return

            if rename_movie(parts[1], parts[2]):
                safe_send(chat_id, "Renamed successfully")
                log_to_discord("File renamed", "list", "info")
            else:
                safe_send(chat_id, "Movie not found")
                log_to_discord("Rename failed", "list", "warning")

            return

        # ===== STATS =====
        if text == '/stats' and user_id == ADMIN_ID:
            s = get_stats()

            safe_send(chat_id, f"Movies: {s['movie_count']}\nUsers: {s['user_count']}")
            log_to_discord("Stats checked", "list", "info")
            return

        # ===== HEALTH =====
        if text == '/health' and user_id == ADMIN_ID:
            p = psutil.Process()
            mem = p.memory_info().rss / 1024 / 1024
            cpu = p.cpu_percent(interval=0.1)

            u = time.time() - start_time
            h = int(u // 3600)
            m = int((u % 3600) // 60)
            s = int(u % 60)

            safe_send(chat_id, f"Uptime: {h}h {m}m {s}s\nRAM: {mem:.2f}MB\nCPU: {cpu:.2f}%")
            log_to_discord("Health checked", "list", "info")
            return

        # ===== START =====
        if text.startswith('/start '):
            name = text.replace('/start ', '').replace('_', ' ')
            movies = load_movies()

            if name in movies:
                send_file(chat_id, movies[name]['file_id'])

                log_to_discord(
                    "File accessed",
                    "access",
                    "info",
                    fields={"movie": name}
                )
            else:
                safe_send(chat_id, "Movie not found")
                log_to_discord("Access failed", "access", "warning")

    except Exception as e:
        log_to_discord(
            "Handler crash",
            "status",
            "error",
            fields={"error": str(e)}
        )