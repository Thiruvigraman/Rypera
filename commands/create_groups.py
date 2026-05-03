# file: commands/create_groups.py

from bot import send_message

from database.groups import (
    create_group,
    group_exists
)

from database.movies import load_movies_full

from metadata.group_detector import detect_groups

from webhook import log_to_discord

from utils import get_username


def handle_create_groups(chat_id, user):
    try:
        movies = load_movies_full()

        if not movies:
            send_message(chat_id, "❌ No movies found")
            return

        detected_groups = detect_groups(movies)

        if not detected_groups:
            send_message(chat_id, "❌ No groups detected")
            return

        created = 0
        skipped = 0

        for group in detected_groups:
            already_exists = group_exists(
                title=group["title"],
                season=group["season"],
                quality=group["quality"],
                audio=group["audio"],
                start_episode=group["start_episode"],
                end_episode=group["end_episode"]
            )

            if already_exists:
                skipped += 1
                continue

            create_group(group)

            created += 1

        send_message(
            chat_id,
            (
                "✅ Group creation completed\n\n"
                f"📦 Created: {created}\n"
                f"⏭ Skipped: {skipped}"
            )
        )

        log_to_discord(
            "📦 Groups Created",
            "list",
            "info",
            fields={
                "admin": get_username(user),
                "created": created,
                "skipped": skipped
            }
        )

    except Exception as e:
        print("CREATE GROUPS ERROR:", str(e))

        send_message(
            chat_id,
            "❌ Failed to create groups"
        )