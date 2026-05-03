# file: metadata/group_resolver.py

from collections import OrderedDict

from database.connection import movies_collection


def build_query(filters):
    query = {}

    if filters.get("title"):
        query["title"] = filters["title"]

    if filters.get("quality"):
        query["quality"] = filters["quality"]

    if filters.get("audio"):
        query["audio"] = filters["audio"]

    if filters.get("season") is not None:
        query["season"] = filters["season"]

    start_episode = filters.get("start_episode")
    end_episode = filters.get("end_episode")

    if start_episode is not None and end_episode is not None:
        query["episode"] = {
            "$gte": start_episode,
            "$lte": end_episode
        }

    return query


def remove_duplicate_episodes(files):
    unique = OrderedDict()

    for movie in files:
        episode = movie.get("episode")

        if episode is None:
            continue

        if episode not in unique:
            unique[episode] = movie

    return list(unique.values())


def sort_files(files):
    return sorted(
        files,
        key=lambda x: (
            x.get("season", 0),
            x.get("episode", 0)
        )
    )


def validate_files(files):
    valid = []

    for movie in files:
        if not movie.get("file_id"):
            continue

        valid.append(movie)

    return valid


def detect_missing_episodes(files):
    episodes = []

    for movie in files:
        ep = movie.get("episode")

        if isinstance(ep, int):
            episodes.append(ep)

    if not episodes:
        return []

    episodes = sorted(episodes)

    missing = []

    for i in range(episodes[0], episodes[-1] + 1):
        if i not in episodes:
            missing.append(i)

    return missing


def resolve_group_files(group):
    filters = group.get("filters", {})

    query = build_query(filters)

    cursor = movies_collection.find(query)

    files = list(cursor)

    files = validate_files(files)

    files = remove_duplicate_episodes(files)

    files = sort_files(files)

    missing = detect_missing_episodes(files)

    return {
        "files": files,
        "missing_episodes": missing,
        "count": len(files)
    }