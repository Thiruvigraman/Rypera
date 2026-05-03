# file: handlers/admin_handler.py

from commands.generate_link import handle_generate_link
from commands.delete_movie import handle_delete_movie
from commands.rename_file import handle_rename
from commands.health import handle_health
from commands.search import handle_search
from commands.stats import handle_stats
from commands.top_movies import handle_top_movies
from commands.announcement import handle_announcement
from commands.list_movies import handle_list_movies
from commands.upload_movie import handle_upload_name
from commands.cmd import handle_cmd
from commands.create_groups import (
    handle_create_groups
)


def process_admin_commands(
    text,
    chat_id,
    user,
    user_id,
    pending_delete,
    pending_announcement
):
    if text == "/cmd":
        handle_cmd(chat_id)
        return True

    if text.startswith("/generate_link"):
        handle_generate_link(chat_id, text, user)
        return True

    if text.startswith("/delete_movie"):
        handle_delete_movie(
            chat_id,
            text,
            user_id,
            pending_delete,
            user
        )
        return True

    if text.startswith("/rename_file"):
        handle_rename(chat_id, text, user)
        return True

    if text.startswith("/announce"):
        handle_announcement(
            chat_id,
            text,
            user_id,
            pending_announcement,
            user
        )
        return True

    if text == "/stats":
        handle_stats(chat_id, user)
        return True

    if text == "/top_movies":
        handle_top_movies(chat_id, user)
        return True

    if text == "/health":
        handle_health(chat_id, user)
        return True

    if text == "/list_movies":
        handle_list_movies(chat_id, user)
        return True

    if text == "/create_groups":
        handle_create_groups(chat_id, user)
        return True

    if text.startswith("/gsearch"):
                handle_group_search(
                    chat_id,
                    text.replace("/gsearch", "", 1).strip()
                )
        return


    if text.startswith("/search"):
        handle_search(chat_id, text)
        return True

    

    return False
