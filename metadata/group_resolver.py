#file : metadata/group_resolver.py

from database.connection import (
    MONGO_AVAILABLE,
    movies_collection
)


def movie_matches_group(movie, group):
    metadata = movie.get("metadata", {})
    filters = group.get("filters", {})
    range_data = group.get("range", {})

    # ================= TITLE =================

    if filters.get("title"):
        if metadata.get("title") != filters.get("title"):
            return False

    # ================= AUDIO =================

    if filters.get("audio"):
        if metadata.get("audio") != filters.get("audio"):
            return False

    # ================= QUALITY =================

    if filters.get("quality"):
        if metadata.get("quality") != filters.get("quality"):
            return False

    # ================= SEASON =================

    if filters.get("season") is not None:
        if metadata.get("season") != filters.get("season"):
            return False

    # ================= EPISODE RANGE =================

    episode = metadata.get("episode")

    start_episode = range_data.get("start_episode")
    end_episode = range_data.get("end_episode")

    if episode is not None:
        if start_episode is not None:
            if episode < start_episode:
                return False

        if end_episode is not None:
            if episode > end_episode:
                return False

    return True


def resolve_group_movies(group):
    if not MONGO_AVAILABLE:
        return []

    try:
        matched_movies = []

        cursor = movies_collection.find({})

        for movie in cursor:
            if movie_matches_group(movie, group):
                matched_movies.append({
                    "name": movie.get("name"),
                    "file_id": movie.get("file_id"),
                    "token": movie.get("token"),
                    "metadata": movie.get("metadata", {})
                })

        matched_movies.sort(
            key=lambda x: (
                x.get("metadata", {}).get("episode") or 0
            )
        )

        return matched_movies

    except Exception:
        return []
