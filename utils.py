# file: utils.py

from database import get_pending_files
from webhook import log_to_discord


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