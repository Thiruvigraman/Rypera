# file: commands/list_movies.py

from database import load_movies
from webhook import log_to_discord
import requests
from config import BOT_TOKEN
from utils import get_username
username = get_username(user)

PER_PAGE = 10


def send_page(chat_id, page):
    movies = list(load_movies().items())

    total = len(movies)
    pages = (total // PER_PAGE) + (1 if total % PER_PAGE else 0)

    if pages == 0:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": "No movies available"}
        )
        return

    if page < 1 or page > pages:
        return

    start = (page - 1) * PER_PAGE
    chunk = movies[start:start + PER_PAGE]

    text = f"📋 Movies (Page {page}/{pages})\n\n"

    for i, (name, _) in enumerate(chunk, start + 1):
        text += f"{i}. {name}\n"

    buttons = []

    if page > 1:
        buttons.append({"text": "⬅️", "callback_data": f"list_{page-1}"})
    if page < pages:
        buttons.append({"text": "➡️", "callback_data": f"list_{page+1}"})

    keyboard = {"inline_keyboard": [buttons]} if buttons else None

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": keyboard
        }
    )


def handle_list_movies(chat_id, user):
    send_page(chat_id, 1)


    log_to_discord(
        message="📋 Movie List Opened",
        log_type="list",
        severity="info",
        fields={"admin": username}
    )