import os
import requests
from config import BUFFER_API_KEY, BUFFER_PROFILE_IDS, OUTPUT_FILE

_GQL_URL = "https://api.bufferapp.com/graphql"
_UPLOAD_URL = "https://api.bufferapp.com/1/media/upload.json"

_POST_MUTATION = """
mutation CreatePost($input: PostInput!) {
  createPost(input: $input) {
    post {
      id
      status
      scheduledAt
    }
    userErrors {
      message
      field
    }
  }
}
"""

_POST_CAPTIONS = [
    "🎬 Top 10 Funniest Videos Right Now! Which one got you? 😂 #funny #comedy #viral #trending",
    "😂 You NEED to see these! Top 10 funniest clips of the day! #funny #fail #hilarious",
    "🏆 Ranking the FUNNIEST videos on the internet right now! #comedy #viral #funny",
    "💀 These videos had us dying 😂 Top 10 countdown! #funny #fails #comedy #viral",
]

_caption_index = 0


def upload() -> None:
    if not BUFFER_API_KEY:
        print("[uploader] BUFFER_API_KEY not set — skipping")
        return
    if not BUFFER_PROFILE_IDS:
        print("[uploader] BUFFER_PROFILE_IDS empty — skipping")
        return
    if not os.path.exists(OUTPUT_FILE):
        print(f"[uploader] Output file not found: {OUTPUT_FILE}")
        return

    media_url = _upload_media()
    if not media_url:
        return

    for channel_id in BUFFER_PROFILE_IDS:
        _create_post(channel_id, media_url)


def _upload_media() -> str | None:
    """Upload the video file and return a hosted URL for use in GraphQL posts."""
    try:
        with open(OUTPUT_FILE, "rb") as f:
            resp = requests.post(
                _UPLOAD_URL,
                headers={"Authorization": f"Bearer {BUFFER_API_KEY}"},
                files={"file": (os.path.basename(OUTPUT_FILE), f, "video/mp4")},
                timeout=120,
            )
        if not resp.ok:
            print(f"[uploader] Media upload failed ({resp.status_code}): {resp.text[:200]}")
            return None
        data = resp.json()
        url = data.get("url") or data.get("media", {}).get("url")
        print(f"[uploader] Media uploaded — url: {url}")
        return url
    except Exception as e:
        print(f"[uploader] Media upload error: {e}")
        return None


def _create_post(channel_id: str, video_url: str) -> None:
    global _caption_index
    caption = _POST_CAPTIONS[_caption_index % len(_POST_CAPTIONS)]
    _caption_index += 1

    headers = {
        "Authorization": f"Bearer {BUFFER_API_KEY}",
        "Content-Type": "application/json",
    }
    variables = {
        "input": {
            "channelId": channel_id,
            "text": caption,
            "media": [{"url": video_url, "mediaType": "VIDEO"}],
            "publishNow": True,
        }
    }
    try:
        resp = requests.post(
            _GQL_URL,
            json={"query": _POST_MUTATION, "variables": variables},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        errors = result.get("data", {}).get("createPost", {}).get("userErrors", [])
        if errors:
            print(f"[uploader] Post errors for {channel_id}: {errors}")
            return
        post_id = result.get("data", {}).get("createPost", {}).get("post", {}).get("id")
        print(f"[uploader] Posted to channel {channel_id} — post id: {post_id}")
    except Exception as e:
        print(f"[uploader] Post failed for {channel_id}: {e}")
