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


def _safe_fetch(platform: str, fetch_fn) -> list[dict]:
    """A single platform's fetcher (API quota, network, or site changes)
    failing shouldn't take down the whole scheduled run - log it and carry
    on with whatever the other platforms found."""
    try:
        return fetch_fn()
    except Exception as e:
        print(f"  [{platform}] fetch failed, skipping this platform: {e}")
        return []


def run():
    print("=== Step 1: Fetching funny videos ===")
    all_videos: list[dict] = []

    # YouTube's live fetch costs API quota and can hit the daily limit;
    # home_scanner.py already fetched + cached full metadata for everything
    # it pulled, so merge in the R2-cached candidates too. Ranking already
    # gates YouTube on R2 availability below, so this keeps candidates
    # flowing even on a day the quota is exhausted.
    youtube_candidates = {v["id"]: v for v in _safe_fetch("youtube", yt_fetcher.fetch)}
    for v in r2_cache.list_cached_videos("youtube"):
        youtube_candidates.setdefault(v["id"], v)
    all_videos.extend(youtube_candidates.values())

    all_videos.extend(_safe_fetch("facebook", fb_fetcher.fetch))
    all_videos.extend(_safe_fetch("reddit", reddit_fetcher.fetch))
    all_videos.extend(_safe_fetch("dailymotion", dm_fetcher.fetch))
    all_videos.extend(_safe_fetch("twitch", twitch_fetcher.fetch))
    all_videos.extend(_safe_fetch("rumble", rumble_fetcher.fetch))

    # TikTok's own fetch needs cookies CI doesn't have (skips silently if
    # missing). home_scanner.py already fetched + cached full metadata for
    # every clip it pulled from a real signed-in session, so pull TikTok
    # candidates from there too, merged with a live fetch in case cookies
    # ever are configured in CI.
    tiktok_candidates = {v["id"]: v for v in _safe_fetch("tiktok", tt_fetcher.fetch)}
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

    # upload() raises if every channel failed, so reaching here means the
    # video actually went out - keep these clips out of the next ranking
    # for a while instead of letting them win again with just a new rank.
    for v in top10:
        r2_cache.mark_posted(f"{v['platform']}_{v['id']}")

    print("\n✓ Pipeline complete.")


if __name__ == "__main__":
    run()
