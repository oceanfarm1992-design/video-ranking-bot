import yt_dlp
from config import RUMBLE_MAX_FETCH

# Rumble comedy/funny channels — yt-dlp's RumbleChannelIE supports these URLs
_CHANNELS = [
    "https://rumble.com/c/Funny",
    "https://rumble.com/c/FunnyVideos",
    "https://rumble.com/c/Humor",
]


def fetch() -> list[dict]:
    candidates: dict[str, dict] = {}
    for channel_url in _CHANNELS:
        if len(candidates) >= RUMBLE_MAX_FETCH:
            break
        _scrape_channel(channel_url, candidates)
    print(f"[rumble] fetched {len(candidates)} candidates")
    return list(candidates.values())


def _scrape_channel(channel_url: str, out: dict[str, dict]) -> None:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": 10,
        "impersonate": "chrome",
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            entries = info.get("entries") or []
            for entry in entries:
                vid_id = entry.get("id") or ""
                if not vid_id or vid_id in out:
                    continue
                creator = entry.get("uploader") or entry.get("channel") or ""
                out[vid_id] = {
                    "platform": "rumble",
                    "id": vid_id,
                    "title": entry.get("title") or "",
                    "creator": creator,
                    "views": int(entry.get("view_count") or 0),
                    "likes": int(entry.get("like_count") or 0),
                    "video_url": entry.get("webpage_url") or entry.get("url") or "",
                }
    except Exception as e:
        msg = str(e) or "blocked (Rumble requires residential IP/proxy)"
        print(f"[rumble] {channel_url} failed: {msg}")
