# file: commands/migrate_metadata.py

from bot import send_message

from database.connection import movies_collection

from metadata.parser import parse_filename


def handle_migrate_metadata(chat_id):
    updated = 0

    skipped = 0

    cursor = movies_collection.find({})

    for movie in cursor:
        name = movie.get("name")

        if not name:
            skipped += 1
            continue

        metadata = movie.get("metadata")

        if metadata:
            skipped += 1
            continue

        parsed = parse_filename(name)

        movies_collection.update_one(
            {
                "_id": movie["_id"]
            },
            {
                "$set": {
                    "metadata": parsed
                }
            }
        )

        updated += 1

    send_message(
        chat_id,
        (
            f"✅ Metadata migration completed\n\n"
            f"Updated: {updated}\n"
            f"Skipped: {skipped}"
        )
    )