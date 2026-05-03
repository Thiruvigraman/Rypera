# file: scripts/migrate_metadata.py

from database.connection import (
    MONGO_AVAILABLE,
    movies_collection
)

from services.metadata.parser import parse_metadata


def migrate_metadata():
    if not MONGO_AVAILABLE:
        print("MongoDB unavailable")
        return

    total = 0
    updated = 0
    skipped = 0

    print("Starting metadata migration...\n")

    movies = movies_collection.find({})

    for movie in movies:
        total += 1

        name = movie.get("name")

        if not name:
            skipped += 1
            continue

        # already migrated
        if (
            "title" in movie and
            "quality" in movie and
            "audio" in movie
        ):
            skipped += 1
            continue

        metadata = parse_metadata(name)

        try:
            movies_collection.update_one(
                {"_id": movie["_id"]},
                {
                    "$set": {
                        "title": metadata["title"],
                        "episode": metadata["episode"],
                        "season": metadata["season"],
                        "quality": metadata["quality"],
                        "audio": metadata["audio"]
                    }
                }
            )

            updated += 1

            print(f"UPDATED: {name}")
            print(metadata)
            print("-" * 50)

        except Exception as e:
            print(f"FAILED: {name}")
            print(str(e))
            print("-" * 50)

    print("\nMigration completed")
    print(f"Total   : {total}")
    print(f"Updated : {updated}")
    print(f"Skipped : {skipped}")


if __name__ == "__main__":
    migrate_metadata()
