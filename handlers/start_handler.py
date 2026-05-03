# file: handlers/start_handler.py

from bot import send_file

from database import (
    get_movie_by_token,
    increment_movie_access,
    save_access_log
)

from webhook import log_to_discord


def process_start(
    text,
    chat_id,
    user_id,
    user,
    safe_send,
    get_user_name
):
    if not text.startswith("/start "):
        return False

    query = text.split(" ", 1)[1]

    movie = get_movie_by_token(query)

    if movie:
        increment_movie_access(movie["name"])

        updated_movie = get_movie_by_token(query)

        count = 1

        if updated_movie and "access_count" in updated_movie:
            count = updated_movie["access_count"]

        send_file(
            chat_id,
            movie["file_id"],
            get_user_name(user),
            movie["name"],
            count
        )

        save_access_log(user_id, movie["name"])

        return True

    safe_send(chat_id, "❌ Invalid or expired link")

    log_to_discord(
        "Invalid link attempt",
        "access",
        "warning",
        fields={
            "user_id": user_id,
            "query": query
        }
    )

    return True
