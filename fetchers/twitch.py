import requests
from config import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET

_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
_CLIPS_URL = "https://api.twitch.tv/helix/clips"
_GAME_IDS = ["509658", "493591"]  # Just Chatting, IRL

_token: str | None = None


def fetch() -> list[dict]:
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        print("[twitch] Skipped — set TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET to enable")
        return []

    token = _get_token()
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}", "Client-Id": TWITCH_CLIENT_ID}
    candidates: dict[str, dict] = {}
    for game_id in _GAME_IDS:
        _fetch_clips(game_id, headers, candidates)

    print(f"[twitch] fetched {len(candidates)} candidates")
    return list(candidates.values())


def _get_token() -> str | None:
    global _token
    if _token:
        return _token
    try:
        resp = requests.post(_TOKEN_URL, params={
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials",
        }, timeout=10)
        resp.raise_for_status()
        _token = resp.json()["access_token"]
        return _token
    except Exception as e:
        print(f"[twitch] token error: {e}")
        return None


def _fetch_clips(game_id: str, headers: dict, out: dict[str, dict]) -> None:
    try:
        resp = requests.get(_CLIPS_URL, headers=headers,
                            params={"game_id": game_id, "first": 20}, timeout=10)
        resp.raise_for_status()
        for clip in resp.json().get("data", []):
            cid = clip["id"]
            if cid in out:
                continue
            out[cid] = {
                "platform": "twitch",
                "id": cid,
                "title": clip.get("title", ""),
                "creator": clip.get("broadcaster_name", ""),
                "views": int(clip.get("view_count", 0)),
                "likes": 0,
                "video_url": clip.get("url", ""),
            }
    except Exception as e:
        print(f"[twitch] game {game_id} failed: {e}")
