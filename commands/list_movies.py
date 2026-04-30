# file: commands/list_movies.py

from database import load_movies
from bot import edit_message, send_message
from webhook import log_to_discord
from utils import get_username

PER_PAGE = 10


def send_page(chat_id, page, message_id=None):
    movies_dict = load_movies()
    movies = list(movies_dict.items())

    if not movies:
        send_message(chat_id, "No movies available")
        return

    total = len(movies)
    pages = (total + PER_PAGE - 1) // PER_PAGE

    if page < 1 or page > pages:
        return

    start = (page - 1) * PER_PAGE
    chunk = movies[start:start + PER_PAGE]

    text = f"📋 Movies (Page {page}/{pages})\n\n"

    keyboard = []

    for idx, (name, data) in enumerate(chunk, start=start + 1):
        text += f"{idx}. {name}\n"

        token = data.get("token")
        if token:
            keyboard.append([
                {
                    "text": f"🔗 {idx}",
                    "callback_data": f"getlink_{token}"
                }
            ])

    # navigation
    nav = []

    if page > 1:
        nav.append({
            "text": "⬅️",
            "callback_data": f"list_{page-1}"
        })

    if page < pages:
        nav.append({
            "text": "➡️",
            "callback_data": f"list_{page+1}"
        })

    if nav:
        keyboard.append(nav)

    reply_markup = {"inline_keyboard": keyboard} if keyboard else None

    # 🔥 ALWAYS attach buttons to SAME message
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup)
    else:
        res = send_message(chat_id, text, reply_markup=reply_markup)

        # safety: if Telegram returns message_id, we can reuse later
        if res and res.get("ok"):
            return res["result"]["message_id"]


def handle_list_movies(chat_id, user):
    send_page(chat_id, 1)

    log_to_discord(
        "📋 Movie List Opened",
        "list",
        "info",
        fields={"admin": get_username(user)}
    )