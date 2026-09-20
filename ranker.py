import json
from config import TOP_N, RANKINGS_FILE
from seeds_analyzer import load_viral_profile, viral_boost


def rank(all_videos: list[dict]) -> list[dict]:
    profile = load_viral_profile()

    by_platform: dict[str, list[dict]] = {}
    for v in all_videos:
        by_platform.setdefault(v["platform"], []).append(v)

    for videos in by_platform.values():
        max_views = max((v["views"] for v in videos), default=1) or 1
        max_likes = max((v["likes"] for v in videos), default=1) or 1
        for v in videos:
            norm_views = v["views"] / max_views
            norm_likes = v["likes"] / max_likes
            base = norm_views * 0.7 + norm_likes * 0.3
            v["score"] = round(base * viral_boost(v, profile), 6)

    ranked = sorted(all_videos, key=lambda v: v["score"], reverse=True)[:TOP_N]

    for i, v in enumerate(ranked, 1):
        v["rank"] = i

    with open(RANKINGS_FILE, "w") as f:
        json.dump(ranked, f, indent=2)

    print(f"[ranker] Top {len(ranked)} videos saved to {RANKINGS_FILE}")
    return ranked
