# file: commands/list_movies.py

import requests
from database import load_movies
from webhook import log_to_discord
from config import BOT_TOKEN
from utils import get_username

PER_PAGE = 10


def send_page(chat_id, page):
    movies = list(load_movies().items())

    if not movies:
        return

    total = len(movies)
    pages = (total // PER_PAGE) + (1 if total % PER_PAGE else 0)

    if page < 1 or page > pages:
        return

    start = (page - 1) * PER_PAGE
    chunk = movies[start:start + PER_PAGE]

    text = f"📋 Movies (Page {page}/{pages})\n\n"
    for i, (name, _) in enumerate(chunk, start + 1):
        text += f"{i}. {name}\n"

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10
    )


def handle_list_movies(chat_id, user):
    send_page(chat_id, 1)
    username = get_username(user)

    log_to_discord(
        "📋 Movie List Opened",
        "list",
        "info",
        fields={"admin": username}
    )