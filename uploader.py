import os
import requests
from config import BUFFER_API_KEY, BUFFER_ORGANIZATION_ID, OUTPUT_FILE

_GQL_URL = "https://api.bufferapp.com/graphql"

_CREATE_IDEA_MUTATION = """
mutation CreateIdea($orgId: String!, $title: String!, $text: String!) {
  createIdea(input: {
    organizationId: $orgId,
    content: {
      title: $title
      text: $text
    }
  }) {
    ... on Idea {
      id
      content {
        title
        text
      }
    }
  }
}
"""

_TITLES = [
    "Top 10 Funniest Videos Right Now! 😂",
    "You NEED To See These Funny Clips! 💀",
    "Ranking The Internet's Funniest Videos 🏆",
    "These Videos Had Us Dying 😂 Top 10 Countdown",
]

_TEXTS = [
    "🎬 Top 10 Funniest Videos Right Now! Which one got you? 😂 #funny #comedy #viral #trending",
    "😂 You NEED to see these! Top 10 funniest clips of the day! #funny #fail #hilarious",
    "🏆 Ranking the FUNNIEST videos on the internet right now! #comedy #viral #funny",
    "💀 These videos had us dying 😂 Top 10 countdown! #funny #fails #comedy #viral",
]

_index = 0


def upload() -> None:
    if not BUFFER_API_KEY:
        print("[uploader] BUFFER_API_KEY not set — skipping")
        return
    if not BUFFER_ORGANIZATION_ID:
        print("[uploader] BUFFER_ORGANIZATION_ID not set — skipping")
        return
    if not os.path.exists(OUTPUT_FILE):
        print(f"[uploader] Output file not found: {OUTPUT_FILE}")
        return

    _create_idea()


def _create_idea() -> None:
    global _index
    title = _TITLES[_index % len(_TITLES)]
    text = _TEXTS[_index % len(_TEXTS)]
    _index += 1

    headers = {
        "Authorization": f"Bearer {BUFFER_API_KEY}",
        "Content-Type": "application/json",
    }
    variables = {
        "orgId": BUFFER_ORGANIZATION_ID,
        "title": title,
        "text": text,
    }
    try:
        resp = requests.post(
            _GQL_URL,
            json={"query": _CREATE_IDEA_MUTATION, "variables": variables},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        idea = result.get("data", {}).get("createIdea", {})
        idea_id = idea.get("id", "unknown")
        print(f"[uploader] Idea created — id: {idea_id} | {title}")
    except Exception as e:
        print(f"[uploader] createIdea failed: {e}")
