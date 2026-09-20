"""
Analyzes example viral videos to extract a ViralProfile used by the ranker
to boost candidates that share similar engagement patterns and title keywords.
"""

import re
import yt_dlp
from config import SEEDS_FILE

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "this", "that", "be", "are",
    "was", "were", "i", "you", "we", "they", "he", "she", "my", "your",
    "best", "top", "most", "all", "new", "more", "when", "what", "how",
}

_CACHED: dict | None = None


def load_viral_profile() -> dict:
    """
    Returns a ViralProfile dict:
      avg_like_ratio  - mean likes/views across seed videos
      keywords        - set of meaningful title words from seeds
      dur_range       - (min_seconds, max_seconds) of seed clips
    Falls back to safe defaults if seeds file is missing or all fetches fail.
    """
    global _CACHED
    if _CACHED is not None:
        return _CACHED

    urls = _read_seed_urls()
    if not urls:
        _CACHED = _defaults()
        return _CACHED

    ratios: list[float] = []
    all_keywords: list[str] = []
    durations: list[int] = []

    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        for url in urls:
            try:
                info = ydl.extract_info(url, download=False)
                views = info.get("view_count") or 0
                likes = info.get("like_count") or 0
                dur = info.get("duration") or 0
                title = info.get("title", "")

                if views > 0:
                    ratios.append(likes / views)
                if dur > 0:
                    durations.append(dur)
                all_keywords.extend(_extract_keywords(title))
            except Exception as e:
                print(f"[seeds] Could not fetch {url}: {e}")

    if not ratios:
        _CACHED = _defaults()
        return _CACHED

    _CACHED = {
        "avg_like_ratio": sum(ratios) / len(ratios),
        "keywords": set(all_keywords),
        "dur_range": (min(durations) if durations else 5,
                      max(durations) if durations else 60),
    }
    print(
        f"[seeds] Viral profile — avg like ratio: {_CACHED['avg_like_ratio']:.4f}, "
        f"keywords: {sorted(_CACHED['keywords'])}, "
        f"dur range: {_CACHED['dur_range']}"
    )
    return _CACHED


def viral_boost(video: dict, profile: dict) -> float:
    """
    Returns a multiplier (1.0–2.0) based on how closely a candidate
    resembles the viral seed profile.
    """
    boost = 1.0

    # Keyword overlap with seed titles
    title_words = set(_extract_keywords(video.get("title", "")))
    overlap = len(title_words & profile["keywords"])
    if profile["keywords"]:
        boost += 0.5 * (overlap / len(profile["keywords"]))

    # Like-ratio similarity (within 2x of seed average)
    views = video.get("views") or 0
    likes = video.get("likes") or 0
    if views > 0 and profile["avg_like_ratio"] > 0:
        ratio = likes / views
        seed_ratio = profile["avg_like_ratio"]
        similarity = 1.0 - min(abs(ratio - seed_ratio) / seed_ratio, 1.0)
        boost += 0.5 * similarity

    return round(min(boost, 2.0), 4)


def _read_seed_urls() -> list[str]:
    try:
        with open(SEEDS_FILE) as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return []


def _extract_keywords(title: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]{3,}", title.lower())
    return [w for w in words if w not in _STOP_WORDS]


def _defaults() -> dict:
    return {"avg_like_ratio": 0.008, "keywords": set(), "dur_range": (5, 60)}
