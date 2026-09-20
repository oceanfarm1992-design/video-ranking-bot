import os
import yt_dlp
from config import TIKTOK_KEYWORDS, TIKTOK_MAX_FETCH, TIKTOK_COOKIES_FILE

_TAG_BASE = "https://www.tiktok.com/tag/{}"


def fetch() -> list[dict]:
    if not os.path.exists(TIKTOK_COOKIES_FILE):
        print(
            "[tiktok] Skipped — cookies file not found. "
            "Export tiktok_cookies.txt from your browser to enable TikTok."
        )
        return []

    candidates: dict[str, dict] = {}
    for kw in TIKTOK_KEYWORDS:
        if len(candidates) >= TIKTOK_MAX_FETCH:
            break
        _scrape_tag(kw, candidates)

    print(f"[tiktok] fetched {len(candidates)} candidates")
    return list(candidates.values())


def _scrape_tag(keyword: str, out: dict[str, dict]) -> None:
    url = _TAG_BASE.format(keyword.replace(" ", ""))
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": 20,
        "cookiefile": TIKTOK_COOKIES_FILE,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            for entry in info.get("entries") or []:
                vid_id = entry.get("id") or entry.get("url", "").split("/")[-1]
                if not vid_id or vid_id in out:
                    continue
                creator = entry.get("uploader") or entry.get("channel") or ""
                out[vid_id] = {
                    "platform": "tiktok",
                    "id": vid_id,
                    "title": entry.get("title") or entry.get("description") or "",
                    "creator": creator,
                    "views": int(entry.get("view_count") or 0),
                    "likes": int(entry.get("like_count") or 0),
                    "video_url": entry.get("url") or entry.get("webpage_url") or
                                 f"https://www.tiktok.com/@{creator}/video/{vid_id}",
                }
    except Exception as e:
        print(f"[tiktok] tag '{keyword}' failed: {e}")
