import os
import yt_dlp
import r2_cache
from config import DOWNLOADS_DIR, CLIP_DURATION_SEC


def download_all(videos: list[dict]) -> list[dict]:
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    return [{**v, "local_path": _download(v)} for v in videos]


# YouTube and TikTok both block yt-dlp from datacenter/CI IPs (Hetzner,
# GitHub Actions alike) with a bot-check, so a direct download would just
# fail - only R2 (filled by home_scanner.py from a residential IP) works.
_CI_BLOCKED_PLATFORMS = {"youtube", "tiktok"}


def _download(video: dict) -> str | None:
    # Check R2 first regardless of platform: home_scanner.py may have
    # already cached this exact clip (or another instance of it re-fetched
    # later), which is free reuse and a fallback if a platform's direct
    # download starts failing for some other reason later.
    path = _download_from_r2(video)
    if path:
        return path
    if video["platform"] in _CI_BLOCKED_PLATFORMS:
        print(f"[downloader] {video['platform']}_{video['id']} not found in R2 buffer")
        return None
    return _download_direct(video)


def _download_from_r2(video: dict) -> str | None:
    clip_id = f"{video['platform']}_{video['id']}"
    local_path = str(DOWNLOADS_DIR / f"{clip_id}.mp4")
    if r2_cache.download_clip(clip_id, local_path):
        return local_path
    return None


def _download_direct(video: dict) -> str | None:
    out_template = str(DOWNLOADS_DIR / f"{video['platform']}_{video['id']}.%(ext)s")
    captured: list[str] = []

    def _hook(d: dict) -> None:
        if d["status"] == "finished":
            captured.append(d["filename"])

    opts = {
        # Bug fix: removed invalid download_sections dict format.
        # Trimming is handled by processor.py subclip() instead.
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_hook],
        # Skip videos longer than 10 minutes to avoid huge downloads
        "match_filter": yt_dlp.utils.match_filter_func("duration < 600"),
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video["video_url"]])

        # Use hook-captured filename (reliable after merge)
        if captured and os.path.exists(captured[0]):
            return captured[0]

        # Fallback: glob for any file matching our prefix
        prefix = str(DOWNLOADS_DIR / f"{video['platform']}_{video['id']}")
        for ext in ["mp4", "webm", "mkv"]:
            alt = f"{prefix}.{ext}"
            if os.path.exists(alt):
                return alt

        return None
    except Exception as e:
        print(f"[downloader] Failed {video['platform']} {video['id']}: {e}")
        return None
