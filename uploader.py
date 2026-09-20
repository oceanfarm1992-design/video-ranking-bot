import os
import requests
from config import BUFFER_API_KEY, BUFFER_ORGANIZATION_ID, OUTPUT_FILE

_GQL_URL = "https://api.buffer.com/graphql"

_GET_CHANNELS_QUERY = """
query GetChannels($orgId: OrganizationId!) {
  channels(input: { organizationId: $orgId }) {
    id
    name
    service
    isDisconnected
  }
}
"""

_CREATE_POST_MUTATION = """
mutation CreatePost($channelId: ChannelId!, $text: String!) {
  createPost(input: {
    channelId: $channelId
    content: {
      contentType: video
      text: $text
    }
    publishingDetails: {
      publishAt: now
    }
  }) {
    ... on PostCreateSuccess {
      post {
        id
        status
      }
    }
    ... on CoreApiError {
      message
    }
  }
}
"""

_CAPTIONS = [
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
    if not BUFFER_ORGANIZATION_ID:
        print("[uploader] BUFFER_ORGANIZATION_ID not set — skipping")
        return
    if not os.path.exists(OUTPUT_FILE):
        print(f"[uploader] Output file not found: {OUTPUT_FILE}")
        return

    channels = _get_channels()
    if not channels:
        print("[uploader] No connected channels found")
        return

    for ch in channels:
        _post_to_channel(ch)


def _get_channels() -> list[dict]:
    headers = {
        "Authorization": f"Bearer {BUFFER_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(
            _GQL_URL,
            json={"query": _GET_CHANNELS_QUERY, "variables": {"orgId": BUFFER_ORGANIZATION_ID}},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        channels = resp.json().get("data", {}).get("channels", [])
        active = [c for c in channels if not c.get("isDisconnected")]
        print(f"[uploader] Found {len(active)} active channels: {[c['service'] for c in active]}")
        return active
    except Exception as e:
        print(f"[uploader] Failed to fetch channels: {e}")
        return []


def _post_to_channel(channel: dict) -> None:
    global _caption_index
    caption = _CAPTIONS[_caption_index % len(_CAPTIONS)]
    _caption_index += 1

    headers = {
        "Authorization": f"Bearer {BUFFER_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(
            _GQL_URL,
            json={
                "query": _CREATE_POST_MUTATION,
                "variables": {"channelId": channel["id"], "text": caption},
            },
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        payload = result.get("data", {}).get("createPost", {})
        if "message" in payload:
            print(f"[uploader] {channel['service']} ({channel['name']}) error: {payload['message']}")
            return
        post_id = payload.get("post", {}).get("id", "ok")
        status = payload.get("post", {}).get("status", "")
        print(f"[uploader] Posted to {channel['service']} ({channel['name']}) — id: {post_id} status: {status}")
    except Exception as e:
        print(f"[uploader] Failed to post to {channel['service']} ({channel['name']}): {e}")
