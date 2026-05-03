# file: metadata/group_resolver.py

from database.connection import (
    movies_collection
)


def build_query(filters):
    query = {}

    title = filters.get("title")

    if title:
        query["title"] = title

    quality = filters.get("quality")

    if quality:
        query["quality"] = quality

    audio = filters.get("audio")

    if audio:
        query["audio"] = audio

    season = filters.get("season")

    if season is not None:
        query["season"] = season

    start_episode = filters.get("start_episode")

    end_episode = filters.get("end_episode")

    if start_episode is not None and end_episode is not None:
        query["episode"] = {
            "$gte": start_episode,
            "$lte": end_episode
        }

    return query


def resolve_group_files(group):
    filters = group.get("filters", {})

    query = build_query(filters)

    cursor = movies_collection.find(query)

    files = list(cursor)

    files.sort(
        key=lambda x: x.get("episode", 0)
    )

    return files