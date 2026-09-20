import os
import requests
import yt_dlp
from config import TIKTOK_KEYWORDS, TIKTOK_MAX_FETCH, TIKTOK_COOKIES_FILE

_TAG_BASE = "https://www.tiktok.com/tag/{}"

# TikTok Creator Search Insights API — returns trending search terms
_SEARCH_INSIGHTS_URL = (
    "https://www.tiktok.com/api/search/general/preview/"
    "?keyword={}&count=10&offset=0"
)
_TRENDING_HASHTAGS_URL = (
    "https://www.tiktok.com/api/explore/item_list/"
    "?count=10&id=1&type=5&secUid=&maxCursor=0&minCursor=0&shareUid=&lang=en"
)


def fetch() -> list[dict]:
    if not os.path.exists(TIKTOK_COOKIES_FILE):
        print(
            "[tiktok] Skipped — cookies file not found. "
            "Export tiktok_cookies.txt from your browser to enable TikTok."
        )
        return []

    keywords = _get_seo_keywords()
    print(f"[tiktok] SEO keywords: {keywords}")

    candidates: dict[str, dict] = {}
    for kw in keywords:
        if len(candidates) >= TIKTOK_MAX_FETCH:
            break
        _scrape_tag(kw, candidates)

    print(f"[tiktok] fetched {len(candidates)} candidates")
    return list(candidates.values())


def _get_seo_keywords() -> list[str]:
    """Pull trending search suggestions from TikTok's Creator Search Insights."""
    seo_terms: list[str] = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.tiktok.com/",
    }

    cookies = _load_cookies()

    for seed in TIKTOK_KEYWORDS:
        try:
            resp = requests.get(
                _SEARCH_INSIGHTS_URL.format(seed),
                headers=headers,
                cookies=cookies,
                timeout=8,
            )
            if resp.ok:
                data = resp.json()
                # Extract suggested search terms from sug_list or similar keys
                items = (
                    data.get("sug_list")
                    or data.get("data", {}).get("sug_list")
                    or []
                )
                for item in items[:3]:
                    word = item.get("sug_content") or item.get("word") or ""
                    if word and word not in seo_terms:
                        seo_terms.append(word)
        except Exception:
            pass

    # Fall back to configured keywords if SEO fetch returned nothing
    return seo_terms if seo_terms else list(TIKTOK_KEYWORDS)


def _load_cookies() -> dict:
    """Parse Netscape cookie file into a requests-compatible dict."""
    cookies: dict[str, str] = {}
    try:
        with open(TIKTOK_COOKIES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]
    except Exception:
        pass
    return cookies


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
