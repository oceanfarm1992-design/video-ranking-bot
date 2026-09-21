import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
RANKINGS_FILE = str(BASE_DIR / "rankings.json")
SEEDS_FILE = str(BASE_DIR / "viral_seeds.txt")
WATERMARK_FILE = str(BASE_DIR / "assets" / "watermark.webp")
TIKTOK_COOKIES_FILE = str(BASE_DIR / "tiktok_cookies.txt")
OUTPUT_FILE = str(BASE_DIR / "final_ranking_video.mp4")
FACEBOOK_URLS_FILE = str(BASE_DIR / "facebook_urls.txt")
TIKTOK_BRIDGE_SCRIPT = str(BASE_DIR / "tiktok_bridge.js")

TOP_N = 10
CLIP_DURATION_SEC = 10

# YouTube
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CATEGORY_ID = "23"  # Comedy
YOUTUBE_REGION = "US"
YOUTUBE_MAX_FETCH = 30

# TikTok — seed keywords for Creator Search Insights lookup
TIKTOK_KEYWORDS = [
    "funny",
    "comedy",
    "fail",
    "try not to laugh",
    "funny moments",
    "comedy skits",
    "fails compilation",
    "hilarious",
    "prank",
    "bloopers",
]
TIKTOK_MAX_FETCH = 30

# Reddit — create a free app at https://www.reddit.com/prefs/apps (script type)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_SUBREDDITS = ["funny", "PublicFreakout", "instant_regret", "WatchPeopleDieInside", "PeopleFalling"]
REDDIT_MAX_FETCH = 30

# Dailymotion
DAILYMOTION_MAX_FETCH = 25

# Twitch
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

# Rumble
RUMBLE_MAX_FETCH = 20

# Buffer
BUFFER_API_KEY = os.getenv("BUFFER_API_KEY")
BUFFER_ORGANIZATION_ID = os.getenv("BUFFER_ORGANIZATION_ID") or "6aafc6f8778120e5ae005e89"
# ShareMode: addToQueue | shareNext | shareNow | customScheduled
BUFFER_SHARE_MODE = os.getenv("BUFFER_SHARE_MODE") or "addToQueue"

# Video hosting — Buffer must fetch the video from a public URL.
# Uses GitHub Releases on this repo (must be a public repo).
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY") or "oceanfarm1992-design/video-ranking-bot"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
