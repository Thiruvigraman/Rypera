# file: handlers/group_start_handler.py

from database.movies import (
    get_movie_by_token,
    increment_movie_access
)

from database.groups import (
    get_group_by_token
)

from database.group_queue import (
    queue_group_delivery
)

from metadata.group_resolver import (
    resolve_group_files
)

from bot import (
    send_file,
    send_message
)

from webhook import log_to_discord

from utils import get_username


def handle_start_token(chat_id, token, user):
    """
    Handles:
    - single movie tokens
    - grouped tokens
    """

    # ================= SINGLE FILE =================

    movie = get_movie_by_token(token)

    # backward compatibility
    if not movie:
        normalized = (
            token
            .replace("_", " ")
            .strip()
        )

        from database.connection import movies_collection

        movie = movies_collection.find_one({
            "name": {
                "$regex": f"^{normalized}$",
                "$options": "i"
            }
        })

    if movie:
        try:
            increment_movie_access(movie["name"])

            updated_movie = get_movie_by_token(
                movie.get("token")
            ) if movie.get("token") else movie

            count = 1

            if updated_movie:
                count = updated_movie.get(
                    "access_count",
                    1
                )

            send_file(
                chat_id,
                movie["file_id"],
                username=get_username(user),
                movie_name=movie["name"],
                count=count
            )

            return True

        except Exception as e:
            log_to_discord(
                "Single token delivery failed",
                "status",
                "error",
                fields={
                    "error": str(e),
                    "token": token
                }
            )

            send_message(
                chat_id,
                "❌ Failed to send file"
            )

            return True

    # ================= GROUP TOKEN =================

    group = get_group_by_token(token)

    if not group:
        return False

    try:
        files = resolve_group_files(group)

        if not files:
            send_message(
                chat_id,
                "❌ No files found in group"
            )
            return True

        queued = queue_group_delivery(
            chat_id=chat_id,
            files=files,
            username=get_username(user),
            group_name=group.get("title"),
            group_token=token
        )

        if not queued:
            send_message(
                chat_id,
                "❌ Failed to queue delivery"
            )
            return True

        log_to_discord(
            "Grouped delivery queued",
            "access",
            "info",
            fields={
                "group": group.get("title"),
                "count": len(files),
                "chat_id": chat_id
            }
        )

        return True

    except Exception as e:
        log_to_discord(
            "Grouped token delivery failed",
            "status",
            "error",
            fields={
                "error": str(e),
                "token": token
            }
        )

        send_message(
            chat_id,
            "❌ Group delivery failed"
        )

        return True

# backward compatibility
process_group_start = handle_start_token


def is_group_token(token):
    group = get_group_by_token(token)

    return group is not None