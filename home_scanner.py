"""Runs on a home PC (residential IP, not blocked by YouTube's or TikTok's
bot-checks), on a schedule via Windows Task Scheduler — no manual action
needed.

Fetches YouTube, TikTok, and Dailymotion candidates, downloads a short
pre-trimmed clip for any not already cached, uploads to the R2 buffer, and
prunes anything past R2_RETENTION_DAYS. main.py (running in GitHub Actions)
reads from this buffer:
  - YouTube and TikTok downloads are blocked from datacenter IPs, so R2 is
    their only source in CI.
  - Dailymotion downloads work fine directly in CI, but is cached here too
    as a fallback reserve in case its live fetch or download ever fails on
    a given scheduled run - see downloader.py's R2-first check.

TikTok also needs tiktok_cookies.txt on THIS machine, refreshed
automatically every run from your browser's live login session via
cookie_refresh.py — since that reads a real signed-in session on your PC,
not a bot, it isn't subject to the bot-detection that blocked the earlier
VPS login flow.
"""
import argparse
import os
import sys
import tempfile
import time

import yt_dlp

# Video titles routinely contain emoji; Windows' default console encoding
# (cp1252) can't print them and would otherwise crash mid-run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import r2_cache
from config import CLIP_DURATION_SEC, TIKTOK_COOKIES_FILE
from cookie_refresh import refresh_tiktok_cookies
from fetchers import youtube as yt_fetcher
from fetchers import tiktok as tt_fetcher
from fetchers import dailymotion as dm_fetcher
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


def _download_batch(candidates: list[dict], have: set[str]) -> int:
    new_count = 0
    with tempfile.TemporaryDirectory() as tmp_dir:
        for v in candidates:
            if new_count >= _MAX_DOWNLOADS_PER_RUN:
                print(f"  Reached {_MAX_DOWNLOADS_PER_RUN}-clip cap for this batch")
                break
            clip_id = f"{v['platform']}_{v['id']}"
            if clip_id in have:
                continue
            path = _download_short_clip(v, tmp_dir)
            if not path:
                continue
            r2_cache.upload_clip(v, path)
            os.remove(path)
            have.add(clip_id)
            new_count += 1
            print(f"  + cached {clip_id}: {v['title'][:60]}")
    return new_count


def run(batches: int = 1, pause_sec: int = 120) -> None:
    """Fetch candidates once, then download up to `batches` batches of
    _MAX_DOWNLOADS_PER_RUN clips each from that same pool. Only the fetch
    step costs YouTube API quota - downloading is yt-dlp against your own
    residential IP, so extra batches let you fill the R2 buffer over a long
    PC-on session without spending any additional quota."""
    print("=== Refreshing TikTok cookies from browser ===")
    refresh_tiktok_cookies()

    print("\n=== Fetching YouTube candidates ===")
    candidates = yt_fetcher.fetch()
    print(f"  Fetched {len(candidates)} candidates")

    print("\n=== Fetching TikTok candidates ===")
    tiktok_candidates = tt_fetcher.fetch()
    print(f"  Fetched {len(tiktok_candidates)} candidates")
    candidates.extend(tiktok_candidates)

    print("\n=== Fetching Dailymotion candidates ===")
    dailymotion_candidates = dm_fetcher.fetch()
    print(f"  Fetched {len(dailymotion_candidates)} candidates")
    candidates.extend(dailymotion_candidates)

    candidates = [v for v in candidates if is_relevant(v)]
    candidates.sort(key=lambda v: v["views"], reverse=True)
    print(f"  {len(candidates)} on-theme candidates after filtering")

    print("\n=== Checking R2 buffer for what's already cached ===")
    have = r2_cache.list_available_ids()
    print(f"  {len(have)} clips already in buffer")

    total_new = 0
    for batch_num in range(1, batches + 1):
        print(f"\n=== Download batch {batch_num}/{batches} ===")
        new_count = _download_batch(candidates, have)
        total_new += new_count
        print(f"  Added {new_count} new clip(s) this batch")
        if new_count == 0:
            print("  No new candidates left from this fetch — stopping early")
            break
        if batch_num < batches:
            print(f"  Pausing {pause_sec}s before next batch...")
            time.sleep(pause_sec)

    print(f"\n=== Added {total_new} new clip(s) to the buffer total ===")

    print("\n=== Pruning clips older than retention window ===")
    removed = r2_cache.prune_old()
    print(f"  Removed {removed} expired clip(s)")

    print("\n✓ Scan complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fill the R2 clip buffer from YouTube + TikTok + Dailymotion."
    )
    parser.add_argument(
        "--batches", type=int, default=1,
        help="Download batches from a single fetch (default: 1, matches the "
             "normal scheduled-task run). Raise this for an extended PC-on "
             "session — it costs zero extra YouTube API quota since only "
             "the fetch step uses the API.",
    )
    parser.add_argument(
        "--pause", type=int, default=120,
        help="Seconds to pause between batches (default: 120).",
    )
    args = parser.parse_args()
    run(batches=args.batches, pause_sec=args.pause)
