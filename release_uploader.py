import json
import os
import subprocess
from datetime import datetime, timezone

import requests

from config import GITHUB_REPO, GITHUB_TOKEN

_API = f"https://api.github.com/repos/{GITHUB_REPO}"


def github_token() -> str | None:
    if GITHUB_TOKEN:
        return GITHUB_TOKEN
    try:
        return subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout.strip() or None
    except Exception:
        return None


def github_headers() -> dict:
    token = github_token()
    if not token:
        raise RuntimeError("No GitHub token available (set GITHUB_TOKEN or run `gh auth login`)")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def publish_clips_release(videos: list[dict]) -> str:
    """Publish a release tagged clips-<timestamp> containing rankings.json
    plus every video's downloaded clip file. GitHub Actions picks this up
    via the release: published trigger and does the rest (Demucs + MoviePy
    + Buffer). Returns the tag name."""
    tag = f"clips-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    headers = github_headers()

    rel = requests.post(
        f"{_API}/releases",
        headers=headers,
        json={"tag_name": tag, "name": tag, "body": "Raw downloaded clips for GitHub Actions to process."},
        timeout=30,
    )
    rel.raise_for_status()
    release_id = rel.json()["id"]

    payload = json.dumps(videos, indent=2).encode("utf-8")
    _upload_asset(release_id, "rankings.json", payload, "application/json", headers)

    uploaded = 0
    for v in videos:
        path = v.get("local_path")
        if not path or not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            _upload_asset(release_id, os.path.basename(path), f.read(), "video/mp4", headers)
        uploaded += 1

    print(f"[release] Published {tag} with {uploaded} clip(s) + rankings.json")
    return tag


def _upload_asset(release_id: int, name: str, data: bytes, content_type: str, headers: dict) -> None:
    resp = requests.post(
        f"https://uploads.github.com/repos/{GITHUB_REPO}/releases/{release_id}/assets",
        headers={**headers, "Content-Type": content_type},
        params={"name": name},
        data=data,
        timeout=120,
    )
    resp.raise_for_status()
