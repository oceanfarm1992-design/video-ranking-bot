"""Opens the persistent TikTok profile headlessly (keeping the session
warm) and re-exports fresh cookies.txt in Netscape format for yt-dlp.
Meant to run on a schedule (see deploy/crontab.txt) so the manual
login in tiktok_login.py only has to happen once."""
import time
from playwright.sync_api import sync_playwright

PROFILE_DIR = "/opt/video-ranking-bot/tiktok_profile"
COOKIES_OUT = "/opt/video-ranking-bot/tiktok_cookies.txt"


def _write_netscape(cookies: list[dict], path: str) -> None:
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c["domain"]
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        expires = int(c["expires"]) if c.get("expires", -1) and c["expires"] > 0 else 0
        secure = "TRUE" if c.get("secure") else "FALSE"
        lines.append("\t".join([
            domain, flag, c["path"], secure, str(expires), c["name"], c["value"],
        ]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(PROFILE_DIR, headless=True)
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://www.tiktok.com/", timeout=60000)
    time.sleep(3)  # let session/cookies settle

    cookies = context.cookies()
    tiktok_cookies = [c for c in cookies if "tiktok.com" in c["domain"]]

    logged_in = any(c["name"] in ("sessionid", "sid_tt") for c in tiktok_cookies)
    _write_netscape(tiktok_cookies, COOKIES_OUT)
    context.close()

    if logged_in:
        print(f"[tiktok] Session valid — wrote {len(tiktok_cookies)} cookies to {COOKIES_OUT}")
    else:
        print("[tiktok] WARNING: no session cookie found — login may have expired. "
              "Re-run tiktok_login.py over VNC.")
