from fetchers import youtube as yt_fetcher
from fetchers import tiktok as tt_fetcher
from fetchers import facebook as fb_fetcher
from fetchers import reddit as reddit_fetcher
from fetchers import dailymotion as dm_fetcher
from fetchers import twitch as twitch_fetcher
from fetchers import rumble as rumble_fetcher
from ranker import rank
from downloader import download_all
from processor import assemble
from uploader import upload
import r2_cache


def run():
    print("=== Step 1: Fetching funny videos ===")
    all_videos: list[dict] = []
    all_videos.extend(yt_fetcher.fetch())
    all_videos.extend(fb_fetcher.fetch())
    all_videos.extend(reddit_fetcher.fetch())
    all_videos.extend(dm_fetcher.fetch())
    all_videos.extend(twitch_fetcher.fetch())
    all_videos.extend(rumble_fetcher.fetch())

    # TikTok's own fetch needs cookies CI doesn't have (skips silently if
    # missing). home_scanner.py already fetched + cached full metadata for
    # every clip it pulled from a real signed-in session, so pull TikTok
    # candidates from there too, merged with a live fetch in case cookies
    # ever are configured in CI.
    tiktok_candidates = {v["id"]: v for v in tt_fetcher.fetch()}
    for v in r2_cache.list_cached_videos("tiktok"):
        tiktok_candidates.setdefault(v["id"], v)
    all_videos.extend(tiktok_candidates.values())

    print(f"  Fetched {len(all_videos)} candidates across all platforms")

    # YouTube and TikTok downloads are blocked from datacenter IPs (GitHub
    # Actions included) - only rank candidates from those platforms that
    # home_scanner.py has already cached in the R2 buffer, so a Top-N slot
    # never goes to something we can't actually download.
    cached_ids = r2_cache.list_available_ids()
    before = len(all_videos)
    all_videos = [
        v for v in all_videos
        if v["platform"] not in ("youtube", "tiktok")
        or f"{v['platform']}_{v['id']}" in cached_ids
    ]
    dropped = before - len(all_videos)
    if dropped:
        print(f"  Dropped {dropped} YouTube/TikTok candidates not yet cached in R2 buffer")

    print("\n=== Step 2: Ranking top 10 ===")
    top10 = rank(all_videos)
    for v in top10:
        print(f"  #{v['rank']:>2} [{v['platform']:>8}] {v['title'][:55]}")

    print("\n=== Step 3: Downloading clips ===")
    top10 = download_all(top10)

    print("\n=== Step 4: Processing & assembling ===")
    assemble(top10)

    print("\n=== Step 5: Uploading to Buffer ===")
    upload()

    print("\n✓ Pipeline complete.")


if __name__ == "__main__":
    run()
