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


# Phase 1 diagnostic logging.
# Set GROUP_DEBUG = False after diagnosis to silence these Render logs.
GROUP_DEBUG = True


def _group_debug(message):
    if GROUP_DEBUG:
        print(f"[GROUP] {message}", flush=True)


def handle_start_token(chat_id, token, user):
    """
    Handles:
    - single movie tokens
    - grouped tokens
    """

    _group_debug(
        f"START chat_id={chat_id} token={token}"
    )

    # ================= SINGLE FILE =================

    _group_debug("SINGLE_TOKEN_LOOKUP")

    movie = get_movie_by_token(token)

    # backward compatibility
    if not movie:
        _group_debug("SINGLE_TOKEN_NOT_FOUND_TRYING_NAME_LOOKUP")

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
        _group_debug(
            f"SINGLE_MOVIE_FOUND name={movie.get('name')}"
        )

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

            _group_debug(
                f"SINGLE_SEND_START name={movie.get('name')}"
            )

            result = send_file(
                chat_id,
                movie["file_id"],
                username=get_username(user),
                movie_name=movie["name"],
                count=count
            )

            _group_debug(
                f"SINGLE_SEND_RESULT result={result}"
            )

            return True

        except Exception as e:
            _group_debug(
                f"SINGLE_SEND_EXCEPTION error={e}"
            )

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

    _group_debug("GROUP_TOKEN_LOOKUP")

    group = get_group_by_token(token)

    if not group:
        _group_debug("GROUP_NOT_FOUND")
        return False

    _group_debug(
        "GROUP_FOUND "
        f"title={group.get('title')} "
        f"token={group.get('token')} "
        f"count={group.get('count')} "
        f"range={group.get('start_episode')}-{group.get('end_episode')} "
        f"quality={group.get('quality')} "
        f"audio={group.get('audio')} "
        f"arc={group.get('arc')}"
    )

    try:
        _group_debug("RESOLVE_START")

        files = resolve_group_files(group)

        _group_debug(
            f"RESOLVE_RESULT count={len(files)}"
        )

        if not files:
            _group_debug("RESOLVE_EMPTY")

            send_message(
                chat_id,
                "❌ No files found in group"
            )
            return True

        _group_debug(
            f"QUEUE_START count={len(files)}"
        )

        queued = queue_group_delivery(
            chat_id=chat_id,
            files=files,
            username=get_username(user),
            group_name=group.get("title"),
            group_token=token
        )

        _group_debug(
            f"QUEUE_RESULT queued={queued}"
        )

        if not queued:
            _group_debug("QUEUE_FAILED")

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

        _group_debug("GROUP_HANDLER_COMPLETE")

        return True

    except Exception as e:
        _group_debug(
            f"GROUP_EXCEPTION error={e}"
        )

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
