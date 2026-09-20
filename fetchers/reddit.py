import requests
from config import REDDIT_SUBREDDITS, REDDIT_MAX_FETCH, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET

_AUTH_URL = "https://www.reddit.com/api/v1/access_token"
_TOP_URL = "https://oauth.reddit.com/r/{}/top?t=week&limit=25"
_UA = "RankForFun/1.0"

_token: str | None = None


def fetch() -> list[dict]:
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        print("[reddit] Skipped — set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to enable")
        return []

    token = _get_token()
    if not token:
        return []

    headers = {"Authorization": f"bearer {token}", "User-Agent": _UA}
    candidates: dict[str, dict] = {}
    for sub in REDDIT_SUBREDDITS:
        if len(candidates) >= REDDIT_MAX_FETCH:
            break
        _fetch_subreddit(sub, headers, candidates)
    print(f"[reddit] fetched {len(candidates)} candidates")
    return list(candidates.values())


def _get_token() -> str | None:
    global _token
    if _token:
        return _token
    try:
        resp = requests.post(
            _AUTH_URL,
            data={"grant_type": "client_credentials"},
            auth=(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET),
            headers={"User-Agent": _UA},
            timeout=10,
        )
        resp.raise_for_status()
        _token = resp.json()["access_token"]
        return _token
    except Exception as e:
        print(f"[reddit] auth failed: {e}")
        return None


def _fetch_subreddit(sub: str, headers: dict, out: dict[str, dict]) -> None:
    try:
        resp = requests.get(_TOP_URL.format(sub), headers=headers, timeout=10)
        resp.raise_for_status()
        for post in resp.json()["data"]["children"]:
            d = post["data"]
            url = d.get("url", "")
            if not d.get("is_video") and "youtube" not in url and "youtu.be" not in url:
                continue
            vid_id = d["id"]
            if vid_id in out:
                continue
            out[vid_id] = {
                "platform": "reddit",
                "id": vid_id,
                "title": d.get("title", ""),
                "creator": d.get("author", ""),
                "views": int(d.get("score", 0)),
                "likes": int(d.get("ups", 0)),
                "video_url": url,
            }
    except Exception as e:
        print(f"[reddit] r/{sub} failed: {e}")
