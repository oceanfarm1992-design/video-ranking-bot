"""Runs on a home PC (residential IP, not blocked by YouTube's bot-check),
on a schedule via Windows Task Scheduler — no manual action needed.

Fetches YouTube candidates (API — works everywhere), downloads a short
pre-trimmed clip for any not already cached, uploads to the R2 buffer,
and prunes anything past R2_RETENTION_DAYS. Hetzner's fetch_download.py
reads from this buffer instead of downloading from YouTube directly.
"""
import os
import tempfile

import yt_dlp

import r2_cache
from config import CLIP_DURATION_SEC
from fetchers import youtube as yt_fetcher

# A few seconds of margin over CLIP_DURATION_SEC so processor.py's own
# trim always has enough source material regardless of small variance.
_DOWNLOAD_SECONDS = CLIP_DURATION_SEC + 3


def _download_short_clip(video: dict, out_dir: str) -> str | None:
    out_template = os.path.join(out_dir, f"{video['platform']}_{video['id']}.%(ext)s")
    captured: list[str] = []

    def _hook(d: dict) -> None:
        if d["status"] == "finished":
            captured.append(d["filename"])

    opts = {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_hook],
        "match_filter": yt_dlp.utils.match_filter_func("duration < 600"),
        "download_ranges": yt_dlp.utils.download_range_func(None, [(0, _DOWNLOAD_SECONDS)]),
        "force_keyframes_at_cuts": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video["video_url"]])
        if captured and os.path.exists(captured[0]):
            return captured[0]
        prefix = os.path.join(out_dir, f"{video['platform']}_{video['id']}")
        for ext in ("mp4", "webm", "mkv"):
            alt = f"{prefix}.{ext}"
            if os.path.exists(alt):
                return alt
        return None
    except Exception as e:
        print(f"[home_scanner] Download failed {video['platform']} {video['id']}: {e}")
        return None


def run() -> None:
    print("=== Fetching YouTube candidates ===")
    candidates = yt_fetcher.fetch()
    print(f"  Fetched {len(candidates)} candidates")

    print("\n=== Checking R2 buffer for what's already cached ===")
    have = r2_cache.list_available_ids()
    print(f"  {len(have)} clips already in buffer")

    new_count = 0
    with tempfile.TemporaryDirectory() as tmp_dir:
        for v in candidates:
            clip_id = f"{v['platform']}_{v['id']}"
            if clip_id in have:
                continue
            path = _download_short_clip(v, tmp_dir)
            if not path:
                continue
            r2_cache.upload_clip(v, path)
            os.remove(path)
            new_count += 1
            print(f"  + cached {clip_id}: {v['title'][:60]}")

    print(f"\n=== Added {new_count} new clip(s) to the buffer ===")

    print("\n=== Pruning clips older than retention window ===")
    removed = r2_cache.prune_old()
    print(f"  Removed {removed} expired clip(s)")

    print("\n✓ Scan complete.")


if __name__ == "__main__":
    run()
