import os
import requests
from config import (
    BUFFER_API_KEY,
    BUFFER_ORGANIZATION_ID,
    BUFFER_SHARE_MODE,
    OUTPUT_FILE,
)

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
mutation CreatePost(
  $channelId: ChannelId!
  $text: String!
  $videoUrl: String!
  $mode: ShareMode!
  $metadata: PostInputMetaData
) {
  createPost(input: {
    channelId: $channelId
    text: $text
    assets: [{ video: { url: $videoUrl } }]
    mode: $mode
    schedulingType: automatic
    needsApproval: false
    metadata: $metadata
  }) {
    __typename
    ... on PostActionSuccess {
      post { id status channelService dueAt }
    }
    ... on InvalidInputError { message }
    ... on UnauthorizedError { message }
    ... on UnexpectedError { message }
    ... on NotFoundError { message }
    ... on LimitReachedError { message }
    ... on RestProxyError { message code }
  }
}
"""

_CAPTIONS = [
    "🎬 Top 10 Funniest Videos Right Now! Which one got you? 😂 #funny #comedy #viral #trending",
    "😂 You NEED to see these! Top 10 funniest clips of the day! #funny #fail #hilarious",
    "🏆 Ranking the FUNNIEST videos on the internet right now! #comedy #viral #funny",
    "💀 These videos had us dying 😂 Top 10 countdown! #funny #fails #comedy #viral",
]

_TITLES = [
    "Top 10 Funniest Videos Right Now",
    "Top 10 Funniest Clips Of The Day",
    "Ranking The Internet's Funniest Videos",
    "Top 10 Funny Moments Countdown",
]

_caption_index = 0


def _build_metadata(service: str, title: str) -> dict | None:
    """Per-channel required metadata. Buffer rejects posts without these."""
    if service == "youtube":
        return {
            "youtube": {
                "title": title[:100],
                "categoryId": "23",  # Comedy
                "privacy": "public",
                "madeForKids": False,
                "notifySubscribers": True,
            }
        }
    if service == "facebook":
        return {"facebook": {"type": "reel"}}
    if service == "tiktok":
        return {"tiktok": {"title": title[:150]}}
    return None


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

    video_url = _upload_video_to_host()
    if not video_url:
        return

    channels = _get_channels()
    if not channels:
        print("[uploader] No connected channels found")
        return

    succeeded = sum(_post_to_channel(ch, video_url) for ch in channels)
    print(f"[uploader] {succeeded}/{len(channels)} channels posted")
    if succeeded == 0:
        raise RuntimeError("All Buffer posts failed — see errors above")


def _upload_video_to_host() -> str | None:
    """Upload video to catbox.moe — returns a permanent public URL."""
    print("[uploader] Uploading video to file host...")
    try:
        with open(OUTPUT_FILE, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (os.path.basename(OUTPUT_FILE), f, "video/mp4")},
                timeout=120,
            )
        if resp.ok and resp.text.startswith("https://"):
            url = resp.text.strip()
            print(f"[uploader] Video hosted at: {url}")
            return url
        print(f"[uploader] File host upload failed: {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"[uploader] File host upload error: {e}")
        return None


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
        result = resp.json()
        if result.get("errors"):
            msgs = "; ".join(e.get("message", "?") for e in result["errors"])
            raise RuntimeError(f"channels query rejected: {msgs}")
        channels = (result.get("data") or {}).get("channels") or []
        active = [c for c in channels if not c.get("isDisconnected")]
        print(f"[uploader] Found {len(active)} active channels: {[c['service'] for c in active]}")
        return active
    except Exception as e:
        print(f"[uploader] Failed to fetch channels: {e}")
        return []


def _post_to_channel(channel: dict, video_url: str) -> bool:
    global _caption_index
    caption = _CAPTIONS[_caption_index % len(_CAPTIONS)]
    title = _TITLES[_caption_index % len(_TITLES)]
    _caption_index += 1

    headers = {
        "Authorization": f"Bearer {BUFFER_API_KEY}",
        "Content-Type": "application/json",
    }
    variables = {
        "channelId": channel["id"],
        "text": caption,
        "videoUrl": video_url,
        "mode": BUFFER_SHARE_MODE,
        "metadata": _build_metadata(channel["service"], title),
    }
    try:
        resp = requests.post(
            _GQL_URL,
            json={"query": _CREATE_POST_MUTATION, "variables": variables},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()

        if result.get("errors"):
            msgs = "; ".join(e.get("message", "?") for e in result["errors"])
            raise RuntimeError(f"GraphQL query rejected: {msgs}")

        payload = (result.get("data") or {}).get("createPost")
        if not payload:
            raise RuntimeError(f"Empty createPost payload: {result}")

        typename = payload.get("__typename")
        if typename != "PostActionSuccess":
            raise RuntimeError(f"{typename}: {payload.get('message', 'no detail')}")

        post = payload["post"]
        print(
            f"[uploader] OK {channel['service']} ({channel['name']}) "
            f"— id: {post['id']} status: {post['status']}"
        )
        return True
    except Exception as e:
        print(f"[uploader] FAILED {channel['service']} ({channel['name']}): {e}")
        return False
