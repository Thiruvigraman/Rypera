# file: commands/search.py

import math

from database.movies import load_movies_full
from database.groups import search_groups

from bot import (
    send_message,
    edit_message
)

from config import BOT_USERNAME


SEARCH_CACHE = {}

PER_PAGE = 10


def normalize(text):
    return text.lower().strip()


def build_group_section(groups):
    if not groups:
        return ""

    text = "📦 Grouped Results\n\n"

    for index, group in enumerate(groups, start=1):
        title = group.get("title")

        quality = group.get("quality") or "unknown"

        audio = group.get("audio") or "unknown"

        start_ep = group.get("start_episode")

        end_ep = group.get("end_episode")

        token = group.get("token")

        link = (
            f"https://t.me/"
            f"{BOT_USERNAME}"
            f"?start={token}"
        )

        label = title

        if start_ep and end_ep:
            label += f" • {start_ep}-{end_ep}"

        text += (
            f"{index}. 📦 {label}\n"
            f"🎞 {quality} | 🔊 {audio}\n"
            f"🔗 {link}\n\n"
        )

    return text


def group_individual_movies(movies):
    grouped = {}

    for movie in movies:
        metadata = movie.get("metadata", {})

        title = metadata.get("title") or movie.get("name")

        quality = metadata.get("quality") or "unknown"

        audio = metadata.get("audio") or "unknown"

        episode = metadata.get("episode")

        key = (
            title,
            quality,
            audio
        )

        if key not in grouped:
            grouped[key] = []

        grouped[key].append({
            "name": movie.get("name"),
            "token": movie.get("token"),
            "episode": episode,
            "quality": quality,
            "audio": audio
        })

    return grouped


def build_individual_section(grouped, page, total_pages):
    keys = list(grouped.keys())

    start = (page - 1) * PER_PAGE

    chunk_keys = keys[start:start + PER_PAGE]

    text = (
        f"🎬 Individual Results "
        f"(Page {page}/{total_pages})\n\n"
    )

    for key in chunk_keys:
        items = grouped[key]

        title, quality, audio = key

        text += (
            f"🎞 {title} "
            f"| {quality} "
            f"| {audio}\n"
        )

        sorted_items = sorted(
            items,
            key=lambda x: (
                x.get("episode") or 0
            )
        )

        for item in sorted_items:
            token = item.get("token")

            if not token:
                continue

            episode = item.get("episode")

            link = (
                f"https://t.me/"
                f"{BOT_USERNAME}"
                f"?start={token}"
            )

            if episode:
                text += (
                    f"EP {episode} → "
                    f"{link}\n"
                )
            else:
                text += (
                    f"{item['name']} → "
                    f"{link}\n"
                )

        text += "\n"

    return text


def build_keyboard(page, total_pages):
    buttons = []

    if page > 1:
        buttons.append({
            "text": "⬅️",
            "callback_data": f"search_{page-1}"
        })

    if page < total_pages:
        buttons.append({
            "text": "➡️",
            "callback_data": f"search_{page+1}"
        })

    if not buttons:
        return None

    return {
        "inline_keyboard": [buttons]
    }


def send_search_page(
    chat_id,
    page,
    message_id=None
):
    cache = SEARCH_CACHE.get(chat_id)

    if not cache:
        send_message(
            chat_id,
            "❌ Search expired"
        )
        return

    grouped_movies = cache["grouped_movies"]

    grouped_results = cache["grouped_results"]

    total = len(grouped_movies)

    total_pages = max(
        1,
        math.ceil(total / PER_PAGE)
    )

    if page < 1 or page > total_pages:
        return

    text = ""

    if page == 1:
        text += build_group_section(
            grouped_results
        )

    text += build_individual_section(
        grouped_movies,
        page,
        total_pages
    )

    keyboard = build_keyboard(
        page,
        total_pages
    )

    if message_id:
        edit_message(
            chat_id,
            message_id,
            text,
            keyboard
        )
    else:
        send_message(
            chat_id,
            text,
            reply_markup=keyboard
        )


def handle_search(chat_id, text):
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        send_message(
            chat_id,
            "❌ Usage: /search name"
        )
        return

    query = normalize(parts[1])

    all_movies = load_movies_full()

    filtered_movies = []

    for movie in all_movies:
        name = movie.get("name", "")

        metadata = movie.get("metadata", {})

        title = metadata.get("title", "")

        arc = metadata.get("arc", "")

        season = str(
            metadata.get("season", "")
        )

        searchable = (
            f"{name} "
            f"{title} "
            f"{arc} "
            f"{season}"
        ).lower()

        if query in searchable:
            filtered_movies.append(movie)

    if not filtered_movies:
        send_message(
            chat_id,
            "❌ No results found"
        )
        return

    grouped_movies = group_individual_movies(
        filtered_movies
    )

    grouped_results = search_groups(query)

    SEARCH_CACHE[chat_id] = {
        "grouped_movies": grouped_movies,
        "grouped_results": grouped_results
    }

    send_search_page(
        chat_id,
        1
    )