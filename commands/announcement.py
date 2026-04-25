# file: commands/announcement.py

import requests
from bot import send_message
from config import BOT_TOKEN
from webhook import log_to_discord


def get_username(user):
    return f"@{user.get('username')}" if user.get("username") else user.get("first_name", "Admin")


def handle_announcement(chat_id, text, user_id, pending_announcement, user):
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        return send_message(chat_id, "Usage: /announce message")

    announcement = parts[1]
    pending_announcement[user_id] = announcement

    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Confirm", "callback_data": "announce_confirm"},
            {"text": "❌ Cancel", "callback_data": "announce_cancel"}
        ]]
    }

    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"📢 Preview:\n\n{announcement}",
                "reply_markup": keyboard
            },
            timeout=10
        )
    except:
        send_message(chat_id, "⚠️ Failed to send preview")

    username = get_username(user)

    log_to_discord(
        message="📢 Announcement Preview",
        log_type="list",
        severity="info",
        fields={
            "admin": username,
            "length": len(announcement)
        }
    )