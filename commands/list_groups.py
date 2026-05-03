# file: commands/list_groups.py

from bot import send_message

from config import BOT_USERNAME

from database.groups import (
    get_all_groups
)


PER_PAGE = 10


def build_text(groups, page, total_pages):
    start = (page - 1) * PER_PAGE

    chunk = groups[start:start + PER_PAGE]

    text = f"📦 Groups (Page {page}/{total_pages})\n\n"

    for index, group in enumerate(chunk, start=start + 1):
        title = group.get("title")

        season = group.get("season")

        quality = group.get("quality")

        audio = group.get("audio")

        start_ep = group.get("start_episode")

        end_ep = group.get("end_episode")

        token = group.get("token")

        link = f"https://t.me/{BOT_USERNAME}?start={token}"

        label = title

        if season:
            label += f" • Season {season}"

        if start_ep and end_ep:
            label += f" • {start_ep}-{end_ep}"

        text += (
            f"{index}. 📦 {label}\n"
            f"🎞 {quality} | 🔊 {audio}\n"
            f"🔗 {link}\n\n"
        )

    return text


def handle_list_groups(chat_id):
    groups = get_all_groups()

    if not groups:
        send_message(
            chat_id,
            "❌ No groups found"
        )
        return

    total_pages = (
        len(groups) // PER_PAGE
    ) + (
        1 if len(groups) % PER_PAGE else 0
    )

    text = build_text(
        groups,
        1,
        total_pages
    )

    send_message(
        chat_id,
        text
    )