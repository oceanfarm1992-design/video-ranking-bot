"""GitHub Actions entrypoint: triggered by a new clips-* release from
Hetzner. Downloads the raw clips + rankings.json, then runs the heavy
processing (Demucs music removal, MoviePy assembly) and posts to
Buffer. This is where torch/Demucs/MoviePy actually run — GitHub's
runners handle that fine, they just can't download from YouTube."""
import glob
import json
import os

import requests

from config import GITHUB_REPO, DOWNLOADS_DIR
from release_uploader import github_headers
from processor import assemble
from uploader import upload


def _download_release_assets(tag: str) -> list[dict]:
    resp = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{tag}",
        headers=github_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    release = resp.json()

    DOWNLOADS_DIR.mkdir(exist_ok=True)
    rankings: list[dict] | None = None

    for asset in release["assets"]:
        r = requests.get(asset["browser_download_url"], timeout=120)
        r.raise_for_status()
        if asset["name"] == "rankings.json":
            rankings = json.loads(r.content)
        else:
            with open(DOWNLOADS_DIR / asset["name"], "wb") as f:
                f.write(r.content)

    if rankings is None:
        raise RuntimeError(f"Release {tag} had no rankings.json asset")

    for v in rankings:
        matches = glob.glob(str(DOWNLOADS_DIR / f"{v['platform']}_{v['id']}.*"))
        v["local_path"] = matches[0] if matches else None

    return rankings


def run() -> None:
    tag = os.environ["CLIPS_RELEASE_TAG"]
    print(f"=== Downloading release assets for {tag} ===")
    videos = _download_release_assets(tag)
    found = sum(1 for v in videos if v["local_path"])
    print(f"  Resolved {found}/{len(videos)} local clips")

    print("\n=== Processing & assembling ===")
    assemble(videos)

    print("\n=== Uploading to Buffer ===")
    upload()

    print("\n✓ Pipeline complete.")


if __name__ == "__main__":
    run()
