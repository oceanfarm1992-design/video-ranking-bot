import requests
from config import DAILYMOTION_MAX_FETCH

_API = "https://api.dailymotion.com/videos"
_FIELDS = "id,title,owner.screenname,views_total,likes_total,url"
_QUERIES = ["funny moments", "comedy fail", "hilarious"]


def fetch() -> list[dict]:
    candidates: dict[str, dict] = {}
    for query in _QUERIES:
        if len(candidates) >= DAILYMOTION_MAX_FETCH:
            break
        _search(query, candidates)
    print(f"[dailymotion] fetched {len(candidates)} candidates")
    return list(candidates.values())


def _search(query: str, out: dict[str, dict]) -> None:
    params = {
        "fields": _FIELDS,
        "search": query,
        "sort": "visited",
        "limit": 15,
        "language": "en",
        "longer_than": 5,
        "shorter_than": 600,
        "private": 0,
    }
    try:
        resp = requests.get(_API, params=params, timeout=10)
        resp.raise_for_status()
        for item in resp.json().get("list", []):
            vid_id = item.get("id", "")
            if not vid_id or vid_id in out:
                continue
            out[vid_id] = {
                "platform": "dailymotion",
                "id": vid_id,
                "title": item.get("title", ""),
                "creator": item.get("owner.screenname", ""),
                "views": int(item.get("views_total", 0)),
                "likes": int(item.get("likes_total", 0)),
                "video_url": item.get("url", f"https://www.dailymotion.com/video/{vid_id}"),
            }
    except Exception as e:
        print(f"[dailymotion] '{query}' failed: {e}")
