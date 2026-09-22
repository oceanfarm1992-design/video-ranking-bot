"""Launches a persistent, visible Chromium window (via the Xvfb display
this is run under) at TikTok's login page and keeps it open for 10
minutes so a human can log in manually over VNC. The profile directory
persists the session afterward - see tiktok_refresh_cookies.py."""
import sys
from playwright.sync_api import sync_playwright

PROFILE_DIR = "/opt/video-ranking-bot/tiktok_profile"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        PROFILE_DIR,
        headless=False,
        viewport={"width": 1280, "height": 900},
        args=["--start-maximized"],
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://www.tiktok.com/login/phone-or-email/email", timeout=60000)
    print("Browser open at TikTok login. Log in manually over the VNC session.")
    print("This window stays open for 60 minutes.")
    page.wait_for_timeout(60 * 60 * 1000)
    context.close()
