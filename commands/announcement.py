#file: commands/announcement.py

from bot import send_message
from config import BOT_TOKEN
from webhook import log_to_discord
from utils import get_username
import requests


def handle_announcement(chat_id, text, user_id, pending_announcement, user):
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        return send_message(chat_id, "Usage: /announce message")

    announcement = parts[1]
    pending_announcement[user_id] = announcement
    username = get_username(user)

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
    except Exception:
        send_message(chat_id, "⚠️ Failed to send preview")

    log_to_discord(
        "📢 Announcement Preview",
        "list",
        "info",
        fields={"admin": username, "length": len(announcement)}
    )