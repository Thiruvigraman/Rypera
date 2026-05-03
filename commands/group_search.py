# file: commands/group_search.py

from bot import send_message

from database.groups import (
    search_groups
)

from config import BOT_USERNAME


def handle_group_search(chat_id, query):
    groups = search_groups(query)

    if not groups:
        send_message(
            chat_id,
            "❌ No grouped results found"
        )
        return

    text = "📦 Grouped Results\n\n"

    for index, group in enumerate(groups, start=1):
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

    send_message(chat_id, text)