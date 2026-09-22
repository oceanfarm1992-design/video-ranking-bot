"""Cloudflare R2 (S3-compatible) client for the rolling clip buffer.

Two roles:
- home_scanner.py (run on a residential IP) uploads freshly downloaded
  clips here, since YouTube's bot-check does not block home connections.
- downloader.py (on Hetzner/CI, where YouTube blocks yt-dlp) reads
  from here instead of downloading directly.

Layout in the bucket:
  clips/<platform>_<id>.mp4   — the short pre-trimmed clip
  meta/<platform>_<id>.json   — {..video fields.., "uploaded_at": iso8601}
"""
import json
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from config import (
    R2_ENDPOINT,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET,
    R2_RETENTION_DAYS,
)

_client = None


def _s3():
    global _client
    if _client is None:
        if not (R2_ENDPOINT and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY):
            raise RuntimeError(
                "R2 not configured — set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY"
            )
        _client = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _client


def _clip_key(clip_id: str) -> str:
    return f"clips/{clip_id}.mp4"


def _meta_key(clip_id: str) -> str:
    return f"meta/{clip_id}.json"


def exists(clip_id: str) -> bool:
    try:
        _s3().head_object(Bucket=R2_BUCKET, Key=_clip_key(clip_id))
        return True
    except ClientError:
        return False


def upload_clip(video: dict, local_path: str) -> None:
    clip_id = f"{video['platform']}_{video['id']}"
    s3 = _s3()
    s3.upload_file(local_path, R2_BUCKET, _clip_key(clip_id))
    meta = {**video, "uploaded_at": datetime.now(timezone.utc).isoformat()}
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=_meta_key(clip_id),
        Body=json.dumps(meta).encode("utf-8"),
        ContentType="application/json",
    )


def download_clip(clip_id: str, local_path: str) -> bool:
    try:
        _s3().download_file(R2_BUCKET, _clip_key(clip_id), local_path)
        return True
    except ClientError:
        return False


def list_available_ids() -> set[str]:
    """All clip_ids (platform_id) currently cached in the buffer."""
    ids: set[str] = set()
    paginator = _s3().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=R2_BUCKET, Prefix="clips/"):
        for obj in page.get("Contents", []):
            name = obj["Key"].removeprefix("clips/").removesuffix(".mp4")
            if name:
                ids.add(name)
    return ids


def mark_posted(clip_id: str) -> None:
    """Record that a clip was included in a posted ranking video, so
    list_recently_posted() can keep it out of future rankings for a while."""
    _s3().put_object(
        Bucket=R2_BUCKET,
        Key=f"posted/{clip_id}.json",
        Body=json.dumps({"posted_at": datetime.now(timezone.utc).isoformat()}).encode("utf-8"),
        ContentType="application/json",
    )


def list_recently_posted(within_days: int) -> set[str]:
    """clip_ids (platform_id) posted within the last `within_days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)
    ids: set[str] = set()
    s3 = _s3()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=R2_BUCKET, Prefix="posted/"):
        for obj in page.get("Contents", []):
            body = s3.get_object(Bucket=R2_BUCKET, Key=obj["Key"])["Body"].read()
            posted_at = datetime.fromisoformat(json.loads(body)["posted_at"])
            if posted_at >= cutoff:
                ids.add(obj["Key"].removeprefix("posted/").removesuffix(".json"))
    return ids


def list_cached_videos(platform: str) -> list[dict]:
    """Full video metadata for every cached clip on one platform.

    Used for platforms (e.g. TikTok) whose fetch step itself needs cookies
    that CI doesn't have — home_scanner.py already fetched and cached this
    metadata from a real signed-in session, so CI can rank it without
    re-fetching.
    """
    videos: list[dict] = []
    s3 = _s3()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=R2_BUCKET, Prefix=f"meta/{platform}_"):
        for obj in page.get("Contents", []):
            body = s3.get_object(Bucket=R2_BUCKET, Key=obj["Key"])["Body"].read()
            videos.append(json.loads(body))
    return videos


def prune_old(retention_days: int = R2_RETENTION_DAYS) -> int:
    """Delete clips (and their metadata) older than retention_days. Returns count removed."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    s3 = _s3()
    removed = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=R2_BUCKET, Prefix="meta/"):
        for obj in page.get("Contents", []):
            body = s3.get_object(Bucket=R2_BUCKET, Key=obj["Key"])["Body"].read()
            meta = json.loads(body)
            uploaded_at = datetime.fromisoformat(meta["uploaded_at"])
            if uploaded_at < cutoff:
                clip_id = obj["Key"].removeprefix("meta/").removesuffix(".json")
                s3.delete_object(Bucket=R2_BUCKET, Key=_clip_key(clip_id))
                s3.delete_object(Bucket=R2_BUCKET, Key=obj["Key"])
                removed += 1
    return removed
