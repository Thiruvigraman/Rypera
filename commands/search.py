# file: commands/search.py

import math
import re

from bot import (
    edit_message,
    send_message
)

from config import BOT_USERNAME

from database.groups import search_groups
from database.movies import load_movies

SEARCH_CACHE = {}

PER_PAGE = 10


def normalize(text):
    return text.lower().strip()


# ================= OLD PARSER =================

def parse_name(name):
    name_lower = name.lower()

    quality_match = re.search(
        r'(480p|720p|1080p|hdrip|bluray)',
        name_lower
    )

    quality = (
        quality_match.group(1)
        if quality_match
        else "unknown"
    )

    se_match = re.search(
        r's(\d+)e(\d+)',
        name_lower
    )

    if se_match:
        return {
            "type": "season",
            "key": f"S{se_match.group(1)}E{se_match.group(2)}",
            "quality": quality
        }

    ep_match = re.search(
        r'\b(\d{3,4})\b',
        name_lower
    )

    if ep_match:
        return {
            "type": "episode",
            "key": ep_match.group(1),
            "quality": quality
        }

    return {
        "type": "other",
        "key": name,
        "quality": quality
    }


# ================= OLD FILE GROUPING =================

def group_movies(movies):
    grouped = {}

    for name, data in movies.items():
        parsed = parse_name(name)

        key = parsed["key"]

        quality = parsed["quality"]

        if key not in grouped:
            grouped[key] = []

        grouped[key].append({
            "name": name,
            "quality": quality,
            "file_id": data["file_id"],
            "token": data.get("token")
        })

    return grouped


# ================= GROUPED SEARCH =================

def build_group_section(groups):
    text = ""

    for group in groups:
        title = group.get("title") or "Unknown"

        quality = group.get("quality") or "unknown"

        audio = group.get("audio") or "unknown"

        season = group.get("season")

        arc = group.get("arc")

        start_ep = group.get("start_episode")

        end_ep = group.get("end_episode")

        token = group.get("token")

        link = (
            f"https://t.me/"
            f"{BOT_USERNAME}"
            f"?start={token}"
        )

        label = None

        if arc:
            label = arc

        elif season:
            label = f"Season {season}"

        else:
            label = f"Episodes {start_ep}-{end_ep}"

        text += (
            f"📦 {title}\n"
            f"🎞 {label}\n"
            f"📺 {quality}\n"
            f"🎧 {audio}\n"
            f"🔗 {link}\n\n"
        )

    return text


# ================= OLD TEXT =================

def build_file_text(groups, page, total_pages):
    keys = list(groups.keys())

    start = (page - 1) * PER_PAGE

    chunk_keys = keys[start:start + PER_PAGE]

    text = (
        f"🎬 File Results "
        f"(Page {page}/{total_pages})\n\n"
    )

    for key in chunk_keys:
        items = groups[key]

        text += f"🎬 {key}\n"

        for item in items:
            link = (
                f"https://t.me/"
                f"{BOT_USERNAME}"
                f"?start={item['token']}"
            )

            text += (
                f"{item['quality']} "
                f"→ {link}\n"
            )

        text += "\n"

    return text


# ================= KEYBOARD =================

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

    return {
        "inline_keyboard": [buttons]
    } if buttons else None


# ================= PAGE =================

def send_search_page(chat_id, page, message_id=None):
    cache = SEARCH_CACHE.get(chat_id)

    if not cache:
        send_message(
            chat_id,
            "❌ Search expired"
        )
        return

    grouped_results = cache["grouped_results"]

    file_groups = cache["file_groups"]

    total = len(file_groups)

    total_pages = max(
        1,
        math.ceil(total / PER_PAGE)
    )

    if page < 1 or page > total_pages:
        return

    text = ""

    # grouped section only on first page
    if page == 1 and grouped_results:
        text += "📦 GROUP RESULTS\n\n"

        text += build_group_section(
            grouped_results
        )

        text += "────────────\n\n"

    text += build_file_text(
        file_groups,
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


# ================= MAIN SEARCH =================

def handle_search(chat_id, text):
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        return send_message(
            chat_id,
            "❌ Usage: /search name"
        )

    query = normalize(parts[1])

    # ================= GROUP SEARCH =================

    grouped_results = search_groups(query)

    # ================= OLD FILE SEARCH =================

    movies = load_movies()

    filtered = {
        name: data
        for name, data in movies.items()
        if query in normalize(name)
    }

    if not filtered and not grouped_results:
        return send_message(
            chat_id,
            "❌ No results found"
        )

    file_groups = group_movies(filtered)

    SEARCH_CACHE[chat_id] = {
        "grouped_results": grouped_results,
        "file_groups": file_groups
    }

    send_search_page(chat_id, 1)