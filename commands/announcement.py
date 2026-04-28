#file: commands/announcement.py

from bot import send_message
from webhook import log_to_discord
from utils import get_username


def handle_announcement(chat_id, text, user_id, pending_announcement, user):
    try:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "❌ Usage: /announce <message>")
            return

        announcement = parts[1]
        pending_announcement[user_id] = announcement

        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Confirm", "callback_data": "announce_confirm"},
                {"text": "❌ Cancel", "callback_data": "announce_cancel"}
            ]]
        }

        send_message(chat_id, f"📢 Preview:\n\n{announcement}", reply_markup=keyboard)

        log_to_discord(
            "📢 Announcement Preview",
            "list",
            "info",
            fields={"admin": get_username(user), "length": len(announcement)}
        )

    except Exception:
        send_message(chat_id, "❌ Failed to process announcement")