from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY, YOUTUBE_CATEGORY_ID, YOUTUBE_REGION, YOUTUBE_MAX_FETCH


def fetch() -> list[dict]:
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    candidates: dict[str, dict] = {}

    _fetch_chart(youtube, candidates)

    for query in ["funny moments", "comedy fail", "hilarious"]:
        _fetch_search(youtube, query, candidates)

    return list(candidates.values())


def _fetch_chart(youtube, out: dict[str, dict]) -> None:
    resp = youtube.videos().list(
        part="snippet,statistics",
        chart="mostPopular",
        videoCategoryId=YOUTUBE_CATEGORY_ID,
        regionCode=YOUTUBE_REGION,
        maxResults=YOUTUBE_MAX_FETCH,
    ).execute()
    _parse_items(resp.get("items", []), out)


def _fetch_search(youtube, query: str, out: dict[str, dict]) -> None:
    search_resp = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        videoCategoryId=YOUTUBE_CATEGORY_ID,
        regionCode=YOUTUBE_REGION,
        order="viewCount",
        maxResults=YOUTUBE_MAX_FETCH,
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
    if not video_ids:
        return

    detail_resp = youtube.videos().list(
        part="snippet,statistics",
        id=",".join(video_ids),
    ).execute()
    _parse_items(detail_resp.get("items", []), out)


def _parse_items(items: list, out: dict[str, dict]) -> None:
    for item in items:
        vid_id = item["id"]
        if vid_id in out:
            continue
        stats = item.get("statistics", {})
        out[vid_id] = {
            "platform": "youtube",
            "id": vid_id,
            "title": item["snippet"]["title"],
            "creator": item["snippet"]["channelTitle"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "video_url": f"https://www.youtube.com/watch?v={vid_id}",
        }
