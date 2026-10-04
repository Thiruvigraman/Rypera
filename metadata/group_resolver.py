from database.movies import load_movies_full


# Phase 1 diagnostic logging.
# Set GROUP_DEBUG = False after diagnosis to silence these Render logs.
GROUP_DEBUG = True


def _group_debug(message):
    if GROUP_DEBUG:
        print(f"[GROUP] {message}", flush=True)


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
    _group_debug(
        "LOAD_MOVIES_START"
    )

    movies = load_movies_full()

    _group_debug(
        f"MOVIES_LOADED count={len(movies)}"
    )

    matched = []

    for movie in movies:
        if movie_matches_group(movie, group):
            matched.append(movie)

    _group_debug(
        f"MATCHED count={len(matched)}"
    )

    matched = deduplicate_movies(matched)

    _group_debug(
        f"DEDUPLICATED count={len(matched)}"
    )

    matched = sort_movies(matched)

    _group_debug(
        f"SORTED count={len(matched)}"
    )

    return matched
