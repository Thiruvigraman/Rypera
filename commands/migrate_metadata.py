from bot import send_message

from database.connection import (
    MONGO_AVAILABLE,
    movies_collection
)

from database.groups import refresh_groups_after_metadata_migration

from metadata.parser import parse_filename


def handle_migrate_metadata(chat_id):
    """
    Recalculate metadata for every stored movie and then refresh groups.
    """
    if not MONGO_AVAILABLE:
        send_message(
            chat_id,
            "❌ MongoDB is unavailable. Metadata migration was not run."
        )
        return

    updated = 0
    unchanged = 0
    skipped = 0
    failed = 0

    try:
        for movie in movies_collection.find({}):
            name = movie.get("name")

            if not name:
                skipped += 1
                continue

            try:
                parsed = parse_filename(name)
                old_metadata = movie.get("metadata", {})

                if old_metadata == parsed:
                    unchanged += 1
                    continue

                movies_collection.update_one(
                    {"_id": movie["_id"]},
                    {"$set": {"metadata": parsed}}
                )
                updated += 1

            except Exception:
                failed += 1

        group_result = refresh_groups_after_metadata_migration()

        send_message(
            chat_id,
            (
                "✅ Metadata migration completed\n\n"
                f"🎬 Updated: {updated}\n"
                f"⏭ Unchanged: {unchanged}\n"
                f"⚠️ Skipped: {skipped}\n"
                f"❌ Failed: {failed}\n\n"
                f"📦 Groups updated: {group_result['updated']}\n"
                f"📦 Groups split: {group_result['split']}\n"
                f"📦 Groups created: {group_result['created']}\n"
                f"📦 Group failures: {group_result['failed']}"
            )
        )

    except Exception as e:
        send_message(
            chat_id,
            f"❌ Metadata migration failed: {e}"
        )
