# file: metadata/group_detector.py

from collections import defaultdict


MIN_GROUP_SIZE = 3


def build_group_key(movie):
    metadata = movie.get("metadata", {})

    return (
        metadata.get("title"),
        metadata.get("season"),
        metadata.get("quality"),
        metadata.get("audio"),
        metadata.get("arc")
    )


def detect_groups(movies):
    grouped = defaultdict(list)

    for movie in movies:
        metadata = movie.get("metadata", {})

        episode = metadata.get("episode")

        if episode is None:
            continue

        key = build_group_key(movie)

        grouped[key].append(movie)

    results = []

    for key, items in grouped.items():
        sorted_items = sorted(
            items,
            key=lambda x: x["metadata"].get("episode", 0)
        )

        current_group = []

        previous_episode = None

        for movie in sorted_items:
            episode = movie["metadata"].get("episode")

            if previous_episode is None:
                current_group.append(movie)

            elif episode == previous_episode + 1:
                current_group.append(movie)

            else:
                if len(current_group) >= MIN_GROUP_SIZE:
                    results.append(
                        build_group_data(current_group)
                    )

                current_group = [movie]

            previous_episode = episode

        if len(current_group) >= MIN_GROUP_SIZE:
            results.append(
                build_group_data(current_group)
            )

    return results


def build_group_data(group):
    first = group[0]

    last = group[-1]

    metadata = first.get("metadata", {})

    arc = metadata.get("arc")

    season = metadata.get("season")

    title = metadata.get("title")

    label = title

    if arc:
        label = f"{title} - {arc} Arc"

    elif season:
        label = f"{title} - Season {season}"

    return {
        "title": label,

        "main_title": title,

        "season": season,

        "arc": arc,

        "quality": metadata.get("quality"),

        "audio": metadata.get("audio"),

        "start_episode": group[0]["metadata"].get("episode"),

        "end_episode": group[-1]["metadata"].get("episode"),

        "count": len(group),

        "movies": [
            {
                "name": movie.get("name"),
                "file_id": movie.get("file_id"),
                "episode": movie["metadata"].get("episode")
            }
            for movie in group
        ]
    }