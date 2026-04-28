# file: commands/list_movies.py

from database import load_movies
from bot import edit_message, send_message
from webhook import log_to_discord
from utils import get_username

PER_PAGE = 10


def send_page(chat_id, page, message_id=None):
    movies = list(load_movies().items())

    if not movies:
        send_message(chat_id, "No movies available")
        return

    total = len(movies)
    pages = (total // PER_PAGE) + (1 if total % PER_PAGE else 0)

    if page < 1 or page > pages:
        return

    start = (page - 1) * PER_PAGE
    chunk = movies[start:start + PER_PAGE]

    text = f"📋 Movies (Page {page}/{pages})\n\n"

    buttons = []

    for i, (name, data) in enumerate(chunk, start + 1):
        text += f"{i}. {name}\n"

        token = data.get("token")
        if token:
            buttons.append([
                {
                    "text": f"🔗 {i}",
                    "callback_data": f"getlink_{token}"
                }
            ])

    nav_buttons = []

    if page > 1:
        nav_buttons.append({"text": "⬅️", "callback_data": f"list_{page-1}"})

    if page < pages:
        nav_buttons.append({"text": "➡️", "callback_data": f"list_{page+1}"})

    if nav_buttons:
        buttons.append(nav_buttons)

    keyboard = {"inline_keyboard": buttons} if buttons else None

    if message_id:
        edit_message(chat_id, message_id, text, keyboard)
    else:
        send_message(chat_id, text)


def handle_list_movies(chat_id, user):
    send_page(chat_id, 1)

    log_to_discord(
        "📋 Movie List Opened",
        "list",
        "info",
        fields={"admin": get_username(user)}
    )