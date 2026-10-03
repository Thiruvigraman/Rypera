# file: metadata/arc_detector.py
"""
One Piece anime arc detection.

Arc boundaries are episode-based. Keep this table as the single source of
truth for One Piece arc metadata so new uploads and metadata migrations use
the same rules.
"""

ARC_RANGES = {
    "one piece": [
        {"name": "East Blue", "start": 1, "end": 61},
        {"name": "Reverse Mountain", "start": 62, "end": 63},
        {"name": "Whisky Peak", "start": 64, "end": 67},
        {"name": "Little Garden", "start": 70, "end": 77},
        {"name": "Drum Island", "start": 78, "end": 91},
        {"name": "Alabasta", "start": 92, "end": 130},
        {"name": "Post-Alabasta", "start": 131, "end": 135},
        {"name": "Goat Island", "start": 136, "end": 138},
        {"name": "Ruluka Island", "start": 139, "end": 143},
        {"name": "Jaya", "start": 144, "end": 152},
        {"name": "Skypiea", "start": 153, "end": 195},
        {"name": "G-8", "start": 196, "end": 206},
        {"name": "Long Ring Long Land", "start": 207, "end": 219},
        {"name": "Ocean's Dream", "start": 220, "end": 224},
        {"name": "Foxy's Return", "start": 225, "end": 228},
        {"name": "Water 7", "start": 229, "end": 263},
        {"name": "Enies Lobby", "start": 264, "end": 312},
        {"name": "Post-Enies Lobby", "start": 313, "end": 325},
        {"name": "Ice Hunter", "start": 326, "end": 335},
        {"name": "Chopper Man Special", "start": 336, "end": 336},
        {"name": "Thriller Bark", "start": 337, "end": 381},
        {"name": "Spa Island", "start": 382, "end": 384},
        {"name": "Sabaody Archipelago", "start": 385, "end": 405},
        {"name": "Amazon Lily", "start": 408, "end": 421},
        {"name": "Impel Down", "start": 422, "end": 425},
        {"name": "Little East Blue", "start": 426, "end": 429},
        {"name": "Marineford", "start": 457, "end": 489},
        {"name": "Post-War", "start": 490, "end": 491},
        {"name": "Post-War", "start": 493, "end": 516},
        {"name": "Return to Sabaody", "start": 517, "end": 522},
        {"name": "Fish-Man Island", "start": 523, "end": 574},
        {"name": "Z's Ambition", "start": 575, "end": 578},
        {"name": "Punk Hazard", "start": 579, "end": 625},
        {"name": "Caesar Retrieval", "start": 626, "end": 628},
        {"name": "Dressrosa", "start": 629, "end": 746},
        {"name": "Silver Mine", "start": 747, "end": 750},
        {"name": "Zou", "start": 751, "end": 779},
        {"name": "Marine Rookie", "start": 780, "end": 782},
        {"name": "Whole Cake Island", "start": 783, "end": 877},
        {"name": "Reverie", "start": 878, "end": 889},
        {"name": "Wano", "start": 890, "end": 1085},
        {"name": "Egghead", "start": 1086, "end": 1154},
        {"name": "Elbaph", "start": 1155, "end": 9999},
    ]
}

TITLE_ALIASES = {
    "onepiece": "one piece",
    "one piece": "one piece",
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

    return TITLE_ALIASES.get(cleaned, cleaned)


def detect_arc(title, episode):
    if not title or episode is None:
        return None

    normalized = normalize_title(title)

    if normalized not in ARC_RANGES:
        return None

    for arc in ARC_RANGES[normalized]:
        if arc["start"] <= episode <= arc["end"]:
            return arc["name"]

    return None
