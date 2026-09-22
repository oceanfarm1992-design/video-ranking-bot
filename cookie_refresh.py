"""Refreshes tiktok_cookies.txt from a live, already-logged-in browser
session on this PC — no manual "export cookies" step needed.

home_scanner.py calls refresh_tiktok_cookies() at the start of every run,
so cookies stay fresh automatically across its scheduled runs. This file
can also be run standalone (e.g. from its own weekly Task Scheduler entry,
or by hand) if you just want to refresh the cookie file on its own:

    python cookie_refresh.py
    python cookie_refresh.py chrome

Defaults to Edge — Chrome's "App-Bound Encryption" (Chrome 127+) blocks
browser_cookie3 from reading its cookie store even when run as admin;
Edge only needs the process to run elevated, which the scheduled task
running home_scanner.py is configured to do (Task Scheduler > "Run with
highest privileges", no stored password needed since it reuses the
logged-on session).
"""
import http.cookiejar
import sys

import browser_cookie3

from config import TIKTOK_COOKIES_FILE

_BROWSERS = {
    "chrome": browser_cookie3.chrome,
    "edge": browser_cookie3.edge,
    "firefox": browser_cookie3.firefox,
    "brave": browser_cookie3.brave,
}


def refresh_tiktok_cookies(browser: str = "edge") -> bool:
    """Pull the current tiktok.com cookies out of `browser`'s cookie store
    and overwrite TIKTOK_COOKIES_FILE. Returns False (and leaves the
    existing file untouched) if no TikTok cookies were found."""
    if browser not in _BROWSERS:
        print(f"[cookie_refresh] Unknown browser '{browser}', skipping")
        return False

    try:
        cj = _BROWSERS[browser](domain_name="tiktok.com")
    except Exception as e:
        print(f"[cookie_refresh] Could not read {browser} cookies: {e}")
        return False

    jar = http.cookiejar.MozillaCookieJar(TIKTOK_COOKIES_FILE)
    for cookie in cj:
        jar.set_cookie(cookie)

    if len(jar) == 0:
        print(
            f"[cookie_refresh] No TikTok cookies found in {browser} — "
            "make sure you're logged into tiktok.com there."
        )
        return False

    jar.save(ignore_discard=True, ignore_expires=True)
    print(f"[cookie_refresh] Saved {len(jar)} TikTok cookies to {TIKTOK_COOKIES_FILE}")
    return True


if __name__ == "__main__":
    chosen_browser = sys.argv[1] if len(sys.argv) > 1 else "chrome"
    refresh_tiktok_cookies(chosen_browser)
