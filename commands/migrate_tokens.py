# file: commands/migrate_tokens.py

from bot import send_message

from database.connection import movies_collection

from database.movies import generate_unique_token


def handle_migrate_tokens(chat_id):
    updated = 0

    skipped = 0

    cursor = movies_collection.find({})

    for movie in cursor:

        if movie.get("token"):
            skipped += 1
            continue

        token = generate_unique_token()

        movies_collection.update_one(
            {
                "_id": movie["_id"]
            },
            {
                "$set": {
                    "token": token
                }
            }
        )

        updated += 1

    send_message(
        chat_id,
        (
            f"✅ Token migration completed\n\n"
            f"Updated: {updated}\n"
            f"Skipped: {skipped}"
        )
    )