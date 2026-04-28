# file: commands/search.py

import math
import re

from database import load_movies
from bot import send_message, edit_message
from config import BOT_USERNAME

SEARCH_CACHE = {}
PER_PAGE = 10


def normalize(text):
    return text.lower().strip()


def parse_name(name):
    name_lower = name.lower()

    # quality
    quality_match = re.search(r'(480p|720p|1080p|hdrip|bluray)', name_lower)
    quality = quality_match.group(1) if quality_match else "unknown"

    # season episode
    se_match = re.search(r's(\d+)e(\d+)', name_lower)
    if se_match:
        return {
            "type": "season",
            "key": f"S{se_match.group(1)}E{se_match.group(2)}",
            "quality": quality
        }

    # episode number
    ep_match = re.search(r'\b(\d{3,4})\b', name_lower)
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


def build_text(groups, page, total_pages):
    keys = list(groups.keys())
    start = (page - 1) * PER_PAGE
    chunk_keys = keys[start:start + PER_PAGE]

    text = f"🔍 Search Results (Page {page}/{total_pages})\n\n"

    for key in chunk_keys:
        items = groups[key]

        text += f"🎬 {key}\n"

        for item in items:
            link = f"https://t.me/{BOT_USERNAME}?start={item['token']}"
            text += f"{item['quality']} → {link}\n"

        text += "\n"

    return text


def build_keyboard(page, total_pages):
    buttons = []

    if page > 1:
        buttons.append({"text": "⬅️", "callback_data": f"search_{page-1}"})

    if page < total_pages:
        buttons.append({"text": "➡️", "callback_data": f"search_{page+1}"})

    return {"inline_keyboard": [buttons]} if buttons else None


def send_search_page(chat_id, page, message_id=None):
    cache = SEARCH_CACHE.get(chat_id)

    if not cache:
        send_message(chat_id, "❌ Search expired")
        return

    groups = cache["groups"]
    total = len(groups)
    total_pages = math.ceil(total / PER_PAGE)

    if page < 1 or page > total_pages:
        return

    text = build_text(groups, page, total_pages)
    keyboard = build_keyboard(page, total_pages)

    if message_id:
        edit_message(chat_id, message_id, text, keyboard)
    else:
        send_message(chat_id, text)


def handle_search(chat_id, text):
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        return send_message(chat_id, "❌ Usage: /search name")

    query = normalize(parts[1])
    movies = load_movies()

    filtered = {
        name: data
        for name, data in movies.items()
        if query in normalize(name)
    }

    if not filtered:
        return send_message(chat_id, "❌ No results found")

    groups = group_movies(filtered)

    SEARCH_CACHE[chat_id] = {
        "groups": groups
    }

    send_search_page(chat_id, 1)