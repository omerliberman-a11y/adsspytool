"""Interactive helper: opens a headed Chromium, you log into TikTok Ads
manually, the script saves the storage state (cookies + localStorage) to
`<SESSION_STORE_DIR>/tiktok-state.json`.

Subsequent runs of TikTokScraper detect the file and load the session
automatically — unlocking industry filters in the Creative Center, saved
searches, and (anecdotally) higher rate-limits.

Usage:
  poetry run python -m adspy.scrapers.tiktok.capture_session

Steps:
  1. Browser opens at the TikTok Creative Center login.
  2. Log in with the email/handle/password you use for TikTok Ads.
  3. When you see the Creative Center top-ads page, return to the terminal and
     press Enter. State is saved + browser closes.
"""
from __future__ import annotations

import sys
from pathlib import Path

from adspy.config import get_settings


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed. Run: poetry install + playwright install chromium",
              file=sys.stderr)
        return 1

    state_path = Path(get_settings().session_store_dir) / "tiktok-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Opening TikTok Creative Center. Save target: {state_path}")
    print()
    print("Log in if needed, then press Enter here to save the session.")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = ctx.new_page()
        page.goto(
            "https://ads.tiktok.com/business/creativecenter/inspiration/topads/pc/en"
            "?period=30&region=US",
            wait_until="domcontentloaded",
        )
        input("Press Enter when you're done logging in and the top-ads grid is visible: ")
        ctx.storage_state(path=str(state_path))
        browser.close()

    print(f"Saved storage state to {state_path}")
    print("TikTokScraper will use it automatically on next run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
