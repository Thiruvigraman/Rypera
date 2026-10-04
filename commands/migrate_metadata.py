# file: commands/migrate_metadata.py

from bot import send_message

from database.connection import (
    MONGO_AVAILABLE,
    movies_collection
)

from database.groups import (
    refresh_groups_after_metadata_migration
)

from metadata.parser import parse_filename

from webhook import log_to_discord


def handle_migrate_metadata(chat_id):
    """
    Recalculate metadata for every stored movie.

    Existing metadata is intentionally recalculated so changed arc boundaries
    are applied to old files as well as new uploads.
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

                result = movies_collection.update_one(
                    {"_id": movie["_id"]},
                    {"$set": {"metadata": parsed}}
                )

                if result.modified_count:
                    updated += 1
                else:
                    unchanged += 1

            except Exception as e:
                failed += 1

                log_to_discord(
                    "Metadata migration item failed",
                    "status",
                    "error",
                    fields={
                        "movie": name,
                        "error": str(e)
                    }
                )

        group_result = refresh_groups_after_metadata_migration()

        send_message(
            chat_id,
            (
                "✅ Metadata migration completed\n\n"
                f"🎬 Metadata updated: {updated}\n"
                f"⏭ Metadata unchanged: {unchanged}\n"
                f"⚠️ Movies skipped: {skipped}\n"
                f"❌ Movie failures: {failed}\n\n"
                "📦 Existing groups refreshed\n"
                f"• Groups updated: {group_result['updated']}\n"
                f"• Arc splits: {group_result['split']}\n"
                f"• New groups created: {group_result['created']}\n"
                f"• Group failures: {group_result['failed']}"
            )
        )

        log_to_discord(
            "Metadata migration completed",
            "status",
            "info",
            fields={
                "updated": updated,
                "unchanged": unchanged,
                "skipped": skipped,
                "failed": failed,
                "groups_updated": group_result["updated"],
                "group_splits": group_result["split"],
                "groups_created": group_result["created"],
                "group_failures": group_result["failed"],
            }
        )

    except Exception as e:
        log_to_discord(
            "Metadata migration failed",
            "status",
            "error",
            fields={"error": str(e)}
        )

        send_message(
            chat_id,
            f"❌ Metadata migration failed: {e}"
        )
