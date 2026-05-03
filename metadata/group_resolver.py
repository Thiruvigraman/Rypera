# file: metadata/group_resolver.py

from database.movies import load_movies_full


def normalize(value):
    if value is None:
        return None

    return str(value).strip().lower()


def safe_episode(value):
    try:
        return int(value)
    except Exception:
        return None


def get_metadata(movie):
    return movie.get("metadata", {})


def movie_matches_group(movie, group):
    metadata = get_metadata(movie)

    if normalize(metadata.get("title")) != normalize(group.get("main_title")):
        return False

    if normalize(metadata.get("quality")) != normalize(group.get("quality")):
        return False

    if normalize(metadata.get("audio")) != normalize(group.get("audio")):
        return False

    movie_season = metadata.get("season")
    group_season = group.get("season")

    if movie_season != group_season:
        return False

    episode = safe_episode(
        metadata.get("episode")
    )

    if episode is None:
        return False

    start_ep = group.get("start_episode")
    end_ep = group.get("end_episode")

    if episode < start_ep:
        return False

    if episode > end_ep:
        return False

    # arc validation
    group_arc = normalize(group.get("arc"))

    movie_arc = normalize(
        metadata.get("arc")
    )

    if group_arc and movie_arc != group_arc:
        return False

    return True


def sort_movies(movies):
    return sorted(
        movies,
        key=lambda x: (
            x.get("metadata", {}).get("season") or 0,
            x.get("metadata", {}).get("episode") or 0
        )
    )


def deduplicate_movies(movies):
    seen = set()

    results = []

    for movie in movies:
        file_id = movie.get("file_id")

        if not file_id:
            continue

        if file_id in seen:
            continue

        seen.add(file_id)

        results.append(movie)

    return results


def resolve_group_files(group):
    movies = load_movies_full()

    matched = []

    for movie in movies:
        if movie_matches_group(movie, group):
            matched.append(movie)

    matched = deduplicate_movies(matched)

    matched = sort_movies(matched)

    return matched