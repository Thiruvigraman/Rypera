# file: scripts/migrate_metadata.py

from database.connection import movies_collection
from metadata.parser import parse_filename


def migrate_metadata():
    updated = 0
    skipped = 0

    cursor = movies_collection.find({})

    for movie in cursor:
        name = movie.get("name")

        if not name:
            skipped += 1
            continue

        # already migrated
        if movie.get("metadata"):
            skipped += 1
            continue

        metadata = parse_filename(name)

        movies_collection.update_one(
            {"_id": movie["_id"]},
            {
                "$set": {
                    "metadata": metadata
                }
            }
        )

        updated += 1

        print(f"UPDATED: {name}")
        print(metadata)
        print("-" * 50)

    print()
    print("========== DONE ==========")
    print(f"UPDATED : {updated}")
    print(f"SKIPPED : {skipped}")


if __name__ == "__main__":
    migrate_metadata()