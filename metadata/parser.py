#file : metadata/parser.py

import re


QUALITY_PATTERNS = [
    "2160p",
    "1440p",
    "1080p",
    "720p",
    "480p",
    "360p",
    "hdrip",
    "bluray",
    "webrip",
    "web-dl"
]

AUDIO_PATTERNS = [
    "jap",
    "eng",
    "tam",
    "tel",
    "hin",
    "multi"
]


def normalize_text(text):
    return text.lower().strip()


def extract_quality(text):
    text = normalize_text(text)

    for quality in QUALITY_PATTERNS:
        if quality in text:
            return quality

    return None


def extract_audio(text):
    text = normalize_text(text)

    for audio in AUDIO_PATTERNS:
        if audio in text:
            return audio

    return None


def extract_episode(text):
    text = normalize_text(text)

    patterns = [
        r'\be(\d{1,4})\b',
        r'\bep\s?(\d{1,4})\b',
        r'\bepisode\s?(\d{1,4})\b',
        r'\b(\d{3,4})\b'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            try:
                return int(match.group(1))
            except Exception:
                pass

    return None


def extract_season(text):
    text = normalize_text(text)

    patterns = [
        r'season\s?(\d+)',
        r'\bs(\d+)\b'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            try:
                return int(match.group(1))
            except Exception:
                pass

    return None


def clean_title(text):
    text = normalize_text(text)

    remove_patterns = (
        QUALITY_PATTERNS +
        AUDIO_PATTERNS +
        [
            r'\be\d+\b',
            r'\bep\d+\b',
            r'\bepisode\s?\d+\b',
            r'\b\d{3,4}\b',
            r'\bs\d+\b',
            r'season\s?\d+'
        ]
    )

    cleaned = text

    for pattern in remove_patterns:
        cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r'[_\-.]+', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)

    return cleaned.strip()


def detect_content_type(episode, season):
    if season:
        return "season_episode"

    if episode:
        return "episode"

    return "movie"


def parse_filename(filename):
    filename = normalize_text(filename)

    quality = extract_quality(filename)
    audio = extract_audio(filename)
    episode = extract_episode(filename)
    season = extract_season(filename)
    title = clean_title(filename)

    content_type = detect_content_type(
        episode=episode,
        season=season
    )

    return {
        "title": title,
        "episode": episode,
        "season": season,
        "quality": quality,
        "audio": audio,
        "type": content_type
    }
