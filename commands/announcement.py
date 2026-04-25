# file: commands/announcement.py

import requests
from bot import send_message
from config import BOT_TOKEN
from webhook import log_to_discord


def handle_announcement(chat_id, text, user_id, pending_announcement):
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

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": f"📢 Preview:\n\n{announcement}",
            "reply_markup": keyboard
        }
    )

    log_to_discord(
        message="📢 Announcement Preview",
        log_type="list",
        severity="info",
        fields={"admin": user_id}
    )