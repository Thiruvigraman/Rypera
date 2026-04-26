# file: commands/list_movies.py

from database import load_movies
from bot import send_message, edit_message
from webhook import log_to_discord
from utils import get_username

PER_PAGE = 10


def clamp_page(page, total_pages):
    return max(1, min(page, total_pages))


def build_keyboard(page, total_pages):
    buttons = []

    # jump to first
    if page > 1:
        buttons.append({"text": "⏮ 1", "callback_data": "list_1"})

    # jump -5
    if page > 5:
        buttons.append({"text": "⏪ 5", "callback_data": f"list_{page-5}"})

    # prev
    if page > 1:
        buttons.append({"text": "⬅️", "callback_data": f"list_{page-1}"})

    # next
    if page < total_pages:
        buttons.append({"text": "➡️", "callback_data": f"list_{page+1}"})

    # jump +5
    if page + 5 <= total_pages:
        buttons.append({"text": "⏩ 5", "callback_data": f"list_{page+5}"})

    # jump last
    if page < total_pages:
        buttons.append({"text": f"⏭ {total_pages}", "callback_data": f"list_{total_pages}"})

    return {"inline_keyboard": [buttons]} if buttons else None


def send_page(chat_id, page, message_id=None):
    movies = list(load_movies().items())

    if not movies:
        send_message(chat_id, "No movies available")
        return

    total = len(movies)
    total_pages = (total // PER_PAGE) + (1 if total % PER_PAGE else 0)

    page = clamp_page(page, total_pages)

    start = (page - 1) * PER_PAGE
    chunk = movies[start:start + PER_PAGE]

    text = f"📋 Movies (Page {page}/{total_pages})\n\n"

    for i, (name, _) in enumerate(chunk, start + 1):
        text += f"{i}. {name}\n"

    keyboard = build_keyboard(page, total_pages)

    try:
        if message_id:
            edit_message(chat_id, message_id, text, keyboard)
        else:
            send_message(chat_id, text)
    except Exception:
        pass


def handle_list_movies(chat_id, user):
    send_page(chat_id, 1)

    username = get_username(user)

    log_to_discord(
        "📋 Movie List Opened",
        "list",
        "info",
        fields={
            "admin": username
        }
    )