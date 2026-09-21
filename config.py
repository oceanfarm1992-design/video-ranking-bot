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

TOP_N = 5
CLIP_DURATION_SEC = 13  # 5 clips x 13s = 65s total, inside Reels' 90s cap

# Three focused comedy categories, shared across fetchers that take a
# search query (YouTube, Dailymotion). Replaces vague single-word queries
# like "hilarious" that pulled in unrelated long-form content.
CONTENT_QUERIES = [
    # funny animals
    "funny animals",
    "funny dogs",
    "funny cats",
    "funny animal fails",
    "funny dogs compilation",
    "funny cats reaction",
    "funny talking parrot",
    "funny farm animal moments",
    "funny wildlife moments",
    "funny pet fails",
    "funny animal noises",
    "funny horse donkey videos",
    "cute funny baby animals",
    "viral funny animal reels",
    # pranking funny
    "prank gone wrong",
    "prank compilation",
    "funny prank",
    # funny movement (physical comedy / fails)
    "epic fail compilation",
    "clumsy fails",
    "funny dance fails",
]

# Title keywords that disqualify a candidate regardless of engagement —
# filters out movies, news, tutorials etc. that ranked well but aren't
# actually comedy clips (e.g. a "Full Japanese Romantic Movie" that once
# ranked #6 purely because it matched a bare "hilarious" search).
EXCLUDE_TITLE_KEYWORDS = [
    "full movie", "full film", "full episode", "documentary",
    "trailer", "romantic movie", "drama", "news", "tutorial",
    "review", "unboxing", "vlog", "walkthrough", "let's play",
    "part 1", "part 2", "part 3", "part 4", "part 5", "part 6",
    "part 7", "part 8", "part 9", "episode", "ep.",
    "fanfic", "fanfics",
]

# A candidate must match at least one of these to be considered — keeps
# the ranking on the 3 requested categories (animals / pranks / physical
# comedy) instead of whatever else rides in on the generic YouTube
# "trending Comedy" chart (e.g. TV-series clips, anime meme videos).
INCLUDE_TITLE_KEYWORDS = [
    # funny animals
    "animal", "dog", "dogs", "puppy", "cat", "cats", "kitten", "pet",
    "wildlife", "bird", "parrot", "horse", "donkey", "farm animal",
    # pranking funny
    "prank",
    # funny movement / physical comedy
    "fail", "fails", "fall", "falling", "clumsy", "trip", "slip", "stunt",
]

# YouTube
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CATEGORY_ID = "23"  # Comedy
YOUTUBE_REGION = "US"
YOUTUBE_MAX_FETCH = 30

# TikTok — seed keywords for Creator Search Insights lookup
TIKTOK_KEYWORDS = [
    "funny animals",
    "funny dogs",
    "funny cats",
    "prank",
    "prank gone wrong",
    "fails compilation",
    "clumsy fails",
    "try not to laugh",
]
TIKTOK_MAX_FETCH = 30

# Reddit — create a free app at https://www.reddit.com/prefs/apps (script type)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_SUBREDDITS = [
    "funny",
    "PublicFreakout",
    "instant_regret",
    "PeopleFalling",
    "AnimalsBeingDerps",
    "funnyanimals",
    "perfectlycutscreams",
]
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
BUFFER_SHARE_MODE = os.getenv("BUFFER_SHARE_MODE") or "shareNow"

# Video hosting — Buffer must fetch the video from a public URL.
# Uses GitHub Releases on this repo (must be a public repo).
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY") or "oceanfarm1992-design/video-ranking-bot"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
