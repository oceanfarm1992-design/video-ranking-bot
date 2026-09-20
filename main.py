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


def run():
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
