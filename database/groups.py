# file: database/groups.py

import secrets
import string

from webhook import log_to_discord

from .connection import (
    MONGO_AVAILABLE,
    groups_collection
)


def generate_group_token(length=12):
    chars = string.ascii_letters + string.digits

    return ''.join(
        secrets.choice(chars)
        for _ in range(length)
    )


def generate_unique_group_token():
    for _ in range(20):
        token = generate_group_token()

        existing = groups_collection.find_one({
            "token": token
        })

        if not existing:
            return token

    raise RuntimeError("Unable to generate a unique group token")


def _group_document(group_data, token):
    return {
        "title": group_data.get("title"),
        "main_title": group_data.get("main_title"),
        "season": group_data.get("season"),
        "arc": group_data.get("arc"),
        "quality": group_data.get("quality"),
        "audio": group_data.get("audio"),
        "start_episode": group_data.get("start_episode"),
        "end_episode": group_data.get("end_episode"),
        "count": group_data.get("count", 0),
        "movies": group_data.get("movies", []),
        "token": token,
    }


def create_group(group_data):
    if not MONGO_AVAILABLE:
        return None

    try:
        title = group_data.get("title")
        season = group_data.get("season")
        arc = group_data.get("arc")
        quality = group_data.get("quality")
        audio = group_data.get("audio")
        start_episode = group_data.get("start_episode")
        end_episode = group_data.get("end_episode")

        existing = groups_collection.find_one({
            "title": title,
            "season": season,
            "arc": arc,
            "quality": quality,
            "audio": audio,
            "start_episode": start_episode,
            "end_episode": end_episode
        })

        if existing:
            return None

        token = generate_unique_group_token()

        document = _group_document(group_data, token)
        document["access_count"] = 0

        groups_collection.insert_one(document)

        return token

    except Exception as e:
        log_to_discord(
            "Create group failed",
            "status",
            "error",
            fields={"error": str(e)}
        )
        return None


def update_group(token, group_data):
    """Update only fields owned by the group metadata model."""
    if not MONGO_AVAILABLE or not token:
        return False

    try:
        update = _group_document(group_data, token)
        update.pop("token", None)

        result = groups_collection.update_one(
            {"token": token},
            {"$set": update}
        )

        return result.matched_count == 1

    except Exception as e:
        log_to_discord(
            "Update group failed",
            "status",
            "error",
            fields={
                "token": token,
                "error": str(e)
            }
        )
        return False


def _movie_lookup(movies):
    by_file_id = {}
    by_name = {}

    for movie in movies:
        file_id = movie.get("file_id")
        name = movie.get("name")

        if file_id:
            by_file_id[str(file_id)] = movie

        if name:
            by_name[name] = movie

    return by_file_id, by_name


def _group_candidates(group, all_movies, by_file_id, by_name):
    candidates = []

    for item in group.get("movies", []) or []:
        file_id = item.get("file_id")
        name = item.get("name")

        movie = None

        if file_id:
            movie = by_file_id.get(str(file_id))

        if movie is None and name:
            movie = by_name.get(name)

        if movie is not None:
            candidates.append(movie)

    # Older groups may not have a complete movie list.
    if not candidates:
        main_title = str(group.get("main_title") or "").strip().lower()
        quality = str(group.get("quality") or "").strip().lower()
        audio = str(group.get("audio") or "").strip().lower()
        season = group.get("season")
        start_episode = group.get("start_episode")
        end_episode = group.get("end_episode")

        for movie in all_movies:
            metadata = movie.get("metadata", {})

            if str(metadata.get("title") or "").strip().lower() != main_title:
                continue
            if str(metadata.get("quality") or "").strip().lower() != quality:
                continue
            if str(metadata.get("audio") or "").strip().lower() != audio:
                continue
            if metadata.get("season") != season:
                continue

            episode = metadata.get("episode")

            if episode is None:
                continue
            if start_episode is not None and episode < start_episode:
                continue
            if end_episode is not None and episode > end_episode:
                continue

            candidates.append(movie)

    result = []
    seen = set()

    for movie in candidates:
        key = movie.get("file_id") or movie.get("name")

        if not key or key in seen:
            continue

        seen.add(key)
        result.append(movie)

    return result


def refresh_groups_after_metadata_migration():
    """
    Reconcile existing groups after movie metadata is recalculated.

    Existing group tokens are preserved whenever possible. If an old group
    crosses an arc boundary such as Egghead -> Elbaph, the old token remains
    attached to the first resulting segment and a new token is created for
    the next segment.
    """
    if not MONGO_AVAILABLE:
        return {
            "updated": 0,
            "split": 0,
            "created": 0,
            "failed": 0,
        }

    from metadata.group_detector import detect_groups
    from database.movies import load_movies_full

    all_movies = load_movies_full()
    by_file_id, by_name = _movie_lookup(all_movies)

    updated = 0
    split = 0
    created = 0
    failed = 0

    groups = list(groups_collection.find({}))

    for existing in groups:
        token = existing.get("token")

        if not token:
            failed += 1
            continue

        candidates = _group_candidates(
            existing,
            all_movies,
            by_file_id,
            by_name
        )

        if not candidates:
            # Keep the old document rather than deleting its deep link.
            failed += 1
            continue

        detected = detect_groups(candidates)

        if not detected:
            # Preserve small existing groups while correcting their metadata.
            candidates = sorted(
                candidates,
                key=lambda x: x.get("metadata", {}).get("episode", 0)
            )

            first = candidates[0]
            metadata = first.get("metadata", {})
            arc = metadata.get("arc")
            title = metadata.get("title")

            fallback = {
                "title": f"{title} - {arc} Arc" if arc else title,
                "main_title": title,
                "season": metadata.get("season"),
                "arc": arc,
                "quality": metadata.get("quality"),
                "audio": metadata.get("audio"),
                "start_episode": metadata.get("episode"),
                "end_episode": candidates[-1].get("metadata", {}).get("episode"),
                "count": len(candidates),
                "movies": [
                    {
                        "name": movie.get("name"),
                        "file_id": movie.get("file_id"),
                        "episode": movie.get("metadata", {}).get("episode")
                    }
                    for movie in candidates
                ]
            }

            if update_group(token, fallback):
                updated += 1
            else:
                failed += 1

            continue

        if len(detected) > 1:
            split += len(detected) - 1

        # Reuse the existing token for the first segment.
        if update_group(token, detected[0]):
            updated += 1
        else:
            failed += 1

        # Additional segments receive new group tokens.
        for group_data in detected[1:]:
            new_token = create_group(group_data)

            if new_token:
                created += 1
            else:
                failed += 1

    return {
        "updated": updated,
        "split": split,
        "created": created,
        "failed": failed,
    }


def get_group_by_token(token):
    if not MONGO_AVAILABLE:
        return None

    try:
        return groups_collection.find_one({"token": token})
    except Exception:
        return None


def increment_group_access(token):
    if not MONGO_AVAILABLE:
        return

    try:
        groups_collection.update_one(
            {"token": token},
            {"$inc": {"access_count": 1}}
        )
    except Exception:
        pass


def search_groups(query, limit=20):
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(
            groups_collection.find(
                {
                    "title": {
                        "$regex": query,
                        "$options": "i"
                    }
                }
            ).limit(limit)
        )
    except Exception:
        return []


def get_all_groups():
    if not MONGO_AVAILABLE:
        return []

    try:
        return list(
            groups_collection.find().sort("title", 1)
        )
    except Exception:
        return []
