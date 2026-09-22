"""Hetzner entrypoint: fetch, rank, download only. Publishes the raw
clips as a GitHub release so GitHub Actions can pick them up (via the
release: published trigger) and do the heavy processing (Demucs,
MoviePy) plus the Buffer post. Runs on a VPS specifically because
YouTube blocks yt-dlp downloads from GitHub-hosted runner IPs."""
from fetchers import youtube as yt_fetcher
from fetchers import tiktok as tt_fetcher
from fetchers import facebook as fb_fetcher
from fetchers import reddit as reddit_fetcher
from fetchers import dailymotion as dm_fetcher
from fetchers import twitch as twitch_fetcher
from fetchers import rumble as rumble_fetcher
from ranker import rank
from downloader import download_all
from release_uploader import publish_clips_release


def run() -> None:
    print("=== Step 1: Fetching funny videos ===")
    all_videos: list[dict] = []
    all_videos.extend(yt_fetcher.fetch())
    all_videos.extend(tt_fetcher.fetch())
    all_videos.extend(fb_fetcher.fetch())
    all_videos.extend(reddit_fetcher.fetch())
    all_videos.extend(dm_fetcher.fetch())
    all_videos.extend(twitch_fetcher.fetch())
    all_videos.extend(rumble_fetcher.fetch())
    print(f"  Fetched {len(all_videos)} candidates across all platforms")

    print("\n=== Step 2: Ranking top 5 ===")
    top5 = rank(all_videos)
    for v in top5:
        print(f"  #{v['rank']:>2} [{v['platform']:>10}] {v['title'][:60]}")

    print("\n=== Step 3: Downloading clips ===")
    top5 = download_all(top5)
    missing = [v["rank"] for v in top5 if not v.get("local_path")]
    if missing:
        print(f"  Missing downloads for ranks: {missing}")

    print("\n=== Step 4: Publishing clips release for GitHub Actions ===")
    publish_clips_release(top5)

    print("\n✓ Hetzner phase complete — GitHub Actions will process & post.")


if __name__ == "__main__":
    run()
