# file: commands/create_groups.py

from bot import send_message

from database.movies import (
    load_movies_full
)

from database.groups import (
    create_group
)

from metadata.group_detector import (
    detect_groups
)

from webhook import log_to_discord

from utils import get_username


def handle_create_groups(chat_id, user):
    try:
        movies = load_movies_full()

        if not movies:
            send_message(
                chat_id,
                "❌ No movies found"
            )
            return

        groups = detect_groups(movies)

        if not groups:
            send_message(
                chat_id,
                "❌ No groups detected"
            )
            return

        created = 0

        skipped = 0

        for group in groups:
            result = create_group(group)

            if result:
                created += 1
            else:
                skipped += 1

        send_message(
            chat_id,
            (
                "✅ Group creation completed\n\n"
                f"📦 Created: {created}\n"
                f"⏭ Skipped: {skipped}"
            )
        )

        log_to_discord(
            "Groups created",
            "list",
            "info",
            fields={
                "admin": get_username(user),
                "created": created,
                "skipped": skipped
            }
        )

    except Exception as e:
        log_to_discord(
            "Create groups failed",
            "status",
            "error",
            fields={
                "error": str(e)
            }
        )

        send_message(
            chat_id,
            "❌ Failed to create groups"
        )