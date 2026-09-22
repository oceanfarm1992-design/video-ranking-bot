"""Refreshes tiktok_cookies.txt from an already-running, logged-in Edge
window on this PC — no manual "export cookies" step needed.

Chrome and Edge both encrypt cookies at rest (Chromium's "App-Bound
Encryption") in a way browser_cookie3 cannot decrypt even when run as
admin, so reading the cookie *file* directly doesn't work anymore. This
instead connects to a *running* Edge process over its remote-debugging
port and asks it for cookies directly — the browser already has them
decrypted in memory for its own use, so no decryption is needed.

One-time setup on this PC:
  1. Close every Edge window.
  2. Launch Edge with remote debugging enabled, e.g.:
       & "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" --remote-debugging-port=9222
     (or add --remote-debugging-port=9222 to your usual Edge shortcut's
     Target field so it's always on).
  3. Log into tiktok.com in that window and leave it open — home_scanner.py
     calls refresh_tiktok_cookies() at the start of every run, so cookies
     stay fresh as long as this Edge window stays open and logged in.

Can also be run standalone to just refresh the file on its own:

    python cookie_refresh.py
"""
import http.cookiejar
import time

from playwright.sync_api import sync_playwright

from config import TIKTOK_COOKIES_FILE

_CDP_URL = "http://localhost:9222"

# Session cookies (no real expiry) still need *some* future timestamp for
# the Netscape file format yt-dlp reads; this just needs to outlive the
# TikTok session itself, which expires far sooner than this on its own.
_SESSION_COOKIE_TTL_SEC = 60 * 60 * 24 * 30


def _to_cookiejar_cookie(pw_cookie: dict) -> http.cookiejar.Cookie:
    expires = pw_cookie.get("expires")
    if not expires or expires < 0:
        expires = int(time.time()) + _SESSION_COOKIE_TTL_SEC
    else:
        expires = int(expires)

    domain = pw_cookie["domain"]
    return http.cookiejar.Cookie(
        version=0,
        name=pw_cookie["name"],
        value=pw_cookie["value"],
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path=pw_cookie["path"],
        path_specified=True,
        secure=pw_cookie["secure"],
        expires=expires,
        discard=False,
        comment=None,
        comment_url=None,
        rest={"HttpOnly": pw_cookie["httpOnly"]},
        rfc2965=False,
    )


def refresh_tiktok_cookies(cdp_url: str = _CDP_URL) -> bool:
    """Pull tiktok.com cookies out of the Edge window already running with
    remote debugging enabled, and overwrite TIKTOK_COOKIES_FILE. Returns
    False (leaving the existing file untouched) on any failure, so a
    temporarily-closed browser doesn't crash the whole scheduled run."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)
            cookies: list[dict] = []
            for context in browser.contexts:
                cookies.extend(context.cookies("https://www.tiktok.com"))
    except Exception as e:
        print(
            f"[cookie_refresh] Could not connect to Edge at {cdp_url}: {e}\n"
            "  Is Edge running with --remote-debugging-port=9222?"
        )
        return False

    if not cookies:
        print(
            "[cookie_refresh] Edge is running but has no tiktok.com cookies — "
            "make sure you're logged into tiktok.com in that window."
        )
        return False

    jar = http.cookiejar.MozillaCookieJar(TIKTOK_COOKIES_FILE)
    for cookie in cookies:
        jar.set_cookie(_to_cookiejar_cookie(cookie))
    jar.save(ignore_discard=True, ignore_expires=True)
    print(f"[cookie_refresh] Saved {len(jar)} TikTok cookies to {TIKTOK_COOKIES_FILE}")
    return True


if __name__ == "__main__":
    refresh_tiktok_cookies()
