import os
import subprocess
from datetime import datetime, timezone

import requests

from config import (
    BUFFER_API_KEY,
    BUFFER_ORGANIZATION_ID,
    BUFFER_SHARE_MODE,
    GITHUB_REPO,
    GITHUB_TOKEN,
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


def _github_token() -> str | None:
    if GITHUB_TOKEN:
        return GITHUB_TOKEN
    try:
        return subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout.strip() or None
    except Exception:
        return None


def _upload_video_to_host() -> str | None:
    """Publish the video as a GitHub Release asset and return its public URL.

    Buffer fetches the video server-side, so the host must be reachable from
    their infrastructure. catbox.moe blocks datacenter IPs; GitHub's asset CDN
    does not. This requires GITHUB_REPO to be a public repository.
    """
    token = _github_token()
    if not token:
        print("[uploader] No GitHub token (set GITHUB_TOKEN or run `gh auth login`)")
        return None

    tag = f"video-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    api = f"https://api.github.com/repos/{GITHUB_REPO}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        print(f"[uploader] Creating release {tag}...")
        rel = requests.post(
            f"{api}/releases",
            headers=headers,
            json={"tag_name": tag, "name": tag, "body": "Automated ranking video."},
            timeout=30,
        )
        rel.raise_for_status()
        release_id = rel.json()["id"]

        size = os.path.getsize(OUTPUT_FILE)
        print(f"[uploader] Uploading {size / 1_048_576:.1f} MB asset...")
        with open(OUTPUT_FILE, "rb") as f:
            asset = requests.post(
                f"https://uploads.github.com/repos/{GITHUB_REPO}"
                f"/releases/{release_id}/assets",
                headers={**headers, "Content-Type": "video/mp4"},
                params={"name": "ranking_video.mp4"},
                data=f,
                timeout=300,
            )
        asset.raise_for_status()
        url = asset.json()["browser_download_url"]
        print(f"[uploader] Video hosted at: {url}")
        return url
    except Exception as e:
        detail = getattr(e, "response", None)
        if detail is not None:
            print(f"[uploader] GitHub upload failed: {detail.status_code} {detail.text[:300]}")
        else:
            print(f"[uploader] GitHub upload failed: {e}")
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
