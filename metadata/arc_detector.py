# file: metadata/arc_detector.py

ARC_RANGES = {
    "one piece": [
        {
            "name": "East Blue",
            "start": 1,
            "end": 61
        },
        {
            "name": "Alabasta",
            "start": 92,
            "end": 130
        },
        {
            "name": "Enies Lobby",
            "start": 264,
            "end": 312
        },
        {
            "name": "Marineford",
            "start": 457,
            "end": 489
        },
        {
            "name": "Dressrosa",
            "start": 629,
            "end": 746
        },
        {
            "name": "Whole Cake Island",
            "start": 783,
            "end": 877
        },
        {
            "name": "Wano",
            "start": 890,
            "end": 1085
        },
        {
            "name": "Egghead",
            "start": 1086,
            "end": 9999
        }
    ]
}


TITLE_ALIASES = {
    "onepiece": "one piece",
    "one piece": "one piece"
}


def normalize_title(title):
    if not title:
        return ""

    cleaned = (
        title
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )

    return TITLE_ALIASES.get(
        cleaned,
        cleaned
    )


def detect_arc(title, episode):
    if not title:
        return None

    if episode is None:
        return None

    normalized = normalize_title(title)

    if normalized not in ARC_RANGES:
        return None

    arcs = ARC_RANGES[normalized]

    for arc in arcs:
        if arc["start"] <= episode <= arc["end"]:
            return arc["name"]

    return None