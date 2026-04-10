# file: utils.py

from database import get_pending_files
from webhook import log_to_discord
from datetime import datetime
import secrets


# =========================
# CLEANUP SYSTEM (UNCHANGED)
# =========================
def cleanup_pending_files():
    try:
        pending_files = get_pending_files(expiry_minutes=15)

        for file_data in pending_files:
            try:
                from bot import delete_user_messages  # avoid circular import

                delete_user_messages(
                    file_data['chat_id'],
                    file_data['file_message_id'],
                    file_data['warning_message_id']
                )

                log_to_discord(
                    "Cleanup completed",
                    "status",
                    "info",
                    fields={
                        "chat_id": file_data['chat_id']
                    }
                )

            except Exception as e:
                log_to_discord(
                    "Cleanup error (single file)",
                    "status",
                    "error",
                    fields={
                        "chat_id": file_data['chat_id'],
                        "error": str(e)
                    }
                )

    except Exception as e:
        log_to_discord(
            "Cleanup system error",
            "status",
            "error",
            fields={"error": str(e)}
        )


# =========================
# TOKEN GENERATOR
# =========================
def generate_token(length=10):
    return secrets.token_urlsafe(length)


# =========================
# STRUCTURED LOGGING SYSTEM
# =========================
def log_event(event_type, data, level="info"):
    """
    Structured logging wrapper for Discord logs
    """

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # 📦 GROUP CREATED
    if event_type == "group_create":
        log_to_discord(
            "📦 Group Created",
            "group",
            level,
            fields={
                "time": timestamp,
                "anime": data.get("anime"),
                "arc": data.get("title"),
                "range": f"{data.get('start')}-{data.get('end')}",
                "quality": data.get("quality"),
                "files": data.get("count"),
                "token": data.get("token"),
                "admin_id": data.get("admin_id")
            }
        )

    # 📥 GROUP ACCESSED
    elif event_type == "group_access":
        log_to_discord(
            "📥 Group Accessed",
            "usage",
            level,
            fields={
                "time": timestamp,
                "token": data.get("token"),
                "user_id": data.get("user_id"),
                "files_sent": data.get("count")
            }
        )

    # 🗑 GROUP DELETED
    elif event_type == "group_delete":
        log_to_discord(
            "🗑 Group Deleted",
            "group",
            level,
            fields={
                "time": timestamp,
                "token": data.get("token"),
                "admin_id": data.get("admin_id")
            }
        )

    # ⚠️ UNKNOWN EVENT
    else:
        log_to_discord(
            f"Unknown event: {event_type}",
            "system",
            "warning",
            fields={
                "time": timestamp,
                "data": str(data)
            }
        )