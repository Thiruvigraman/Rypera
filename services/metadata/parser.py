#file : services/metadata/parser.py

import re


QUALITY_PATTERNS = [
    "240p",
    "360p",
    "480p",
    "720p",
    "1080p",
    "1440p",
    "2160p",
    "4k",
    "hdrip",
    "bluray",
    "webrip"
]

AUDIO_PATTERNS = [
    "eng",
    "english",
    "tam",
    "tamil",
    "tel",
    "telugu",
    "hin",
    "hindi",
    "mal",
    "malayalam",
    "kan",
    "kannada",
    "jap",
    "japanese"
]


def extract_quality(name: str):
    lower = name.lower()

    for quality in QUALITY_PATTERNS:
        if quality in lower:
            return quality

    return "unknown"


def extract_audio(name: str):
    lower = name.lower()

    for audio in AUDIO_PATTERNS:
        if audio in lower:
            return audio

    return "unknown"


def extract_episode(name: str):
    match = re.search(r"\b(\d{1,4})\b", name)

    if match:
        return int(match.group(1))

    return None


def extract_season(name: str):
    match = re.search(r"s(\d+)", name.lower())

    if match:
        return int(match.group(1))

    return None


def clean_title(name: str):
    cleaned = name

    for item in QUALITY_PATTERNS + AUDIO_PATTERNS:
        cleaned = re.sub(item, "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\b\d{1,4}\b", "", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def parse_metadata(name: str):
    return {
        "title": clean_title(name),
        "episode": extract_episode(name),
        "season": extract_season(name),
        "quality": extract_quality(name),
        "audio": extract_audio(name)
    }
