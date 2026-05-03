# file: handlers/group_start_handler.py

from database.groups import (
    get_group_by_token
)

from database.group_queue import (
    queue_group_delivery
)

from metadata.group_resolver import (
    resolve_group_files
)

from webhook import log_to_discord

from bot import send_message


def is_group_token(token):
    group = get_group_by_token(token)

    return group is not None


def process_group_start(
    token,
    chat_id,
    user,
    user_id
):
    group = get_group_by_token(token)

    if not group:
        return False

    try:
        resolved = resolve_group_files(group)

        files = resolved["files"]

        missing = resolved["missing_episodes"]

        if not files:
            send_message(
                chat_id,
                "❌ Group has no files"
            )

            return True

        username = user.get("first_name", "User")

        queued = queue_group_delivery(
            chat_id=chat_id,
            files=files,
            username=username
        )

        if not queued:
            send_message(
                chat_id,
                "⚠️ Delivery already running"
            )

            return True

        if missing:
            send_message(
                chat_id,
                f"⚠️ Missing Episodes: {missing[:10]}"
            )

        log_to_discord(
            "Grouped delivery started",
            "access",
            "info",
            fields={
                "user_id": user_id,
                "group": group.get("title"),
                "count": len(files)
            }
        )

        return True

    except Exception as e:
        log_to_discord(
            "Group delivery failed",
            "status",
            "error",
            fields={
                "token": token,
                "error": str(e)
            }
        )

        send_message(
            chat_id,
            "❌ Group delivery failed"
        )

        return True