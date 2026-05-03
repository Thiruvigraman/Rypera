 # file: services/metadata/group_detector.py

from collections import defaultdict


MIN_GROUP_SIZE = 3


def build_group_key(movie):
    return (
        movie.get("title"),
        movie.get("quality"),
        movie.get("audio"),
        movie.get("season")
    )


def detect_groups(movies):
    grouped = defaultdict(list)

    # group similar metadata
    for movie in movies:
        episode = movie.get("episode")

        if episode is None:
            continue

        key = build_group_key(movie)

        grouped[key].append(movie)

    results = []

    # process every metadata group
    for key, items in grouped.items():
        sorted_items = sorted(
            items,
            key=lambda x: x.get("episode", 0)
        )

        current_group = []

        previous_episode = None

        for movie in sorted_items:
            episode = movie["episode"]

            if previous_episode is None:
                current_group.append(movie)

            elif episode == previous_episode + 1:
                current_group.append(movie)

            else:
                if len(current_group) >= MIN_GROUP_SIZE:
                    results.append(build_group_data(current_group))

                current_group = [movie]

            previous_episode = episode

        # final flush
        if len(current_group) >= MIN_GROUP_SIZE:
            results.append(build_group_data(current_group))

    return results


def build_group_data(group):
    first = group[0]
    last = group[-1]

    return {
        "title": first.get("title"),

        "quality": first.get("quality"),

        "audio": first.get("audio"),

        "season": first.get("season"),

        "start_episode": first.get("episode"),

        "end_episode": last.get("episode"),

        "count": len(group),

        "movies": group
    }
