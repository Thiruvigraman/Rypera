# file: handlers/group_start_handler.py

from database.groups import (
    get_group_by_token
)

from metadata.group_resolver import (
    resolve_group_files
)

from webhook import log_to_discord


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
        files = resolve_group_files(group)

        if not files:
            return False

        # 🚫 DELIVERY NOT IMPLEMENTED YET
        # future:
        #
        # queue_group_delivery(
        #     chat_id,
        #     files,
        #     user
        # )

        log_to_discord(
            "Group token accessed",
            "access",
            "info",
            fields={
                "user_id": user_id,
                "group": group.get("title"),
                "files": len(files)
            }
        )

        return {
            "group": group,
            "files": files
        }

    except Exception as e:
        log_to_discord(
            "Group start failed",
            "status",
            "error",
            fields={
                "token": token,
                "error": str(e)
            }
        )

        return False