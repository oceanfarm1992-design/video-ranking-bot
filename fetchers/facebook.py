from config import FACEBOOK_URLS_FILE


def fetch() -> list[dict]:
    try:
        with open(FACEBOOK_URLS_FILE, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("[facebook] facebook_urls.txt not found — skipping")
        return []

    videos = []
    for i, line in enumerate(lines):
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        videos.append({
            "platform": "facebook",
            "id": f"fb_{i}",
            "title": f"Facebook Video {i + 1}",
            "creator": "Unknown",
            "views": 0,
            "likes": 0,
            "video_url": url,
        })

    return videos
