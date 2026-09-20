import os
import yt_dlp
from config import DOWNLOADS_DIR, CLIP_DURATION_SEC


def download_all(videos: list[dict]) -> list[dict]:
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    return [{**v, "local_path": _download(v)} for v in videos]


def _download(video: dict) -> str | None:
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
