"""Runs on a home PC (residential IP, not blocked by YouTube's or TikTok's
bot-checks), on a schedule via Windows Task Scheduler — no manual action
needed.

Fetches YouTube and TikTok candidates, downloads a short pre-trimmed clip
for any not already cached, uploads to the R2 buffer, and prunes anything
past R2_RETENTION_DAYS. main.py (running in GitHub Actions) reads from this
buffer instead of downloading directly, which datacenter IPs get blocked
from. TikTok also needs tiktok_cookies.txt on THIS machine (exported once
from your own logged-in browser) — since this runs as a real signed-in
session on your PC, not a bot, that's a normal export, not the VPS login
flow that TikTok's own bot-detection rejected.
"""
import os
import sys
import tempfile

import yt_dlp

# Video titles routinely contain emoji; Windows' default console encoding
# (cp1252) can't print them and would otherwise crash mid-run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import r2_cache
from config import CLIP_DURATION_SEC, TIKTOK_COOKIES_FILE
from fetchers import youtube as yt_fetcher
from fetchers import tiktok as tt_fetcher
from ranker import is_relevant

# A few seconds of margin over CLIP_DURATION_SEC so processor.py's own
# trim always has enough source material regardless of small variance.
_DOWNLOAD_SECONDS = CLIP_DURATION_SEC + 3

# Cap so a single scheduled run finishes in minutes, not hours. The buffer
# still builds up steadily across repeated runs (every few hours via
# Windows Task Scheduler) well ahead of what 3 runs/day x 5 clips needs.
_MAX_DOWNLOADS_PER_RUN = 15


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
    if video["platform"] == "tiktok" and os.path.exists(TIKTOK_COOKIES_FILE):
        opts["cookiefile"] = TIKTOK_COOKIES_FILE

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

    print("\n=== Fetching TikTok candidates ===")
    tiktok_candidates = tt_fetcher.fetch()
    print(f"  Fetched {len(tiktok_candidates)} candidates")
    candidates.extend(tiktok_candidates)

    candidates = [v for v in candidates if is_relevant(v)]
    candidates.sort(key=lambda v: v["views"], reverse=True)
    print(f"  {len(candidates)} on-theme candidates after filtering")

    print("\n=== Checking R2 buffer for what's already cached ===")
    have = r2_cache.list_available_ids()
    print(f"  {len(have)} clips already in buffer")

    new_count = 0
    with tempfile.TemporaryDirectory() as tmp_dir:
        for v in candidates:
            if new_count >= _MAX_DOWNLOADS_PER_RUN:
                print(f"  Reached {_MAX_DOWNLOADS_PER_RUN}-clip cap for this run")
                break
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
