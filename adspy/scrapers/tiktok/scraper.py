"""TikTok Creative Center scraper — via capture-replay.

The `top_ads/v2/list` endpoint requires a JS-computed `user-sign` header. Rather
than reverse-engineer the signing function (it's obfuscated and rotates), we
open the Creative Center page in headless Chromium and let TikTok's own JS sign
the requests; we just observe the resulting JSON responses on the wire.

Public API doc (unofficial): the page renders top-ads cards by calling
  GET /creative_radar_api/v1/top_ads/v2/list
      ?period=7|30|120 &page=N &limit=20 &order_by=for_you &country_code=US

We pivot pagination by navigating the page URL with `&pagination=N` (UI binding),
or by polling the same response after manually clicking "load more". Simplest is
to load the first N pages by opening the URL and waiting for each response in
order.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from adspy.config import get_settings
from adspy.scrapers.base import ScrapeQuery
from adspy.scrapers.scrape_runner import ScrapeRunner
from adspy.utils.errors import ScrapeError
from adspy.utils.logging import get_logger

log = get_logger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


def _session_state_path() -> Path:
    """Path to the optional saved Playwright storage_state for an authenticated TikTok session.

    Captured via `python -m adspy.scrapers.tiktok.capture_session`. If present,
    the scraper loads it before opening pages — unlocking industry-filtered
    Creative Center views, saved searches, and (anecdotally) higher rate limits.
    """
    return Path(get_settings().session_store_dir) / "tiktok-state.json"


class TikTokScraper:
    """Scrapes TikTok Creative Center top-ads via Playwright network interception."""

    def __init__(self, period: int = 30, country: str = "US") -> None:
        if period not in (7, 30, 120):
            raise ValueError(f"period must be 7, 30, or 120 (got {period})")
        self.period = period
        self.country = country.upper()

    def scrape(self, query: ScrapeQuery) -> Iterator[dict[str, Any]]:
        """Yield raw TikTok material dicts. `query.limit` caps total items."""
        run_query = {
            "platform": "tiktok",
            "period": self.period,
            "country": self.country,
            "limit": query.limit,
        }
        with ScrapeRunner(source="tiktok_creative_center", platform="tiktok", query=run_query) as run:
            count = 0
            for raw in self._iter_materials(query.limit):
                count += 1
                # Stamp country/period into the raw dict so the normalizer can use it
                raw["_scraped_country"] = self.country
                raw["_scraped_period_days"] = self.period
                yield raw
            run.record(item_count=count, cost_usd=0.0)

    def _iter_materials(self, max_items: int) -> Iterator[dict[str, Any]]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ScrapeError("playwright not installed") from exc

        page_size = 20
        max_pages = max(1, (max_items + page_size - 1) // page_size)
        emitted = 0

        state_path = _session_state_path()
        context_kwargs: dict[str, Any] = {"user_agent": UA, "locale": "en-US"}
        if state_path.exists():
            log.info("tiktok_using_captured_session", path=str(state_path))
            context_kwargs["storage_state"] = str(state_path)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                ctx = browser.new_context(**context_kwargs)
                page = ctx.new_page()

                # Wire one response handler that captures all top_ads pages we see.
                captured_pages: dict[int, list[dict[str, Any]]] = {}

                def _on_response(resp: Any) -> None:
                    if "/top_ads/v2/list" not in resp.url:
                        return
                    try:
                        body = resp.json()
                    except Exception:
                        return
                    if not isinstance(body, dict) or body.get("code") != 0:
                        return
                    data = body.get("data") or {}
                    pagination = data.get("pagination") or {}
                    page_no = int(pagination.get("page") or 1)
                    materials = data.get("materials") or []
                    captured_pages.setdefault(page_no, []).extend(materials)

                page.on("response", _on_response)

                # Open the Creative Center page — this fires top_ads page 1 automatically.
                url = (
                    "https://ads.tiktok.com/business/creativecenter/inspiration/topads/pc/en"
                    f"?period={self.period}&region={self.country}"
                )
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(2000)

                # Yield page 1
                for m in captured_pages.get(1, []):
                    yield m
                    emitted += 1
                    if emitted >= max_items:
                        return

                # For more pages, navigate the page URL with a page param (TikTok
                # uses ?period=&region=&topadsType=for_you&pagination=N).
                for page_no in range(2, max_pages + 1):
                    next_url = (
                        "https://ads.tiktok.com/business/creativecenter/inspiration/topads/pc/en"
                        f"?period={self.period}&region={self.country}&topadsType=for_you&pagination={page_no}"
                    )
                    page.goto(next_url, wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(1500)
                    new_materials = captured_pages.get(page_no, [])
                    if not new_materials:
                        log.warning("tiktok_no_materials_on_page", page_no=page_no)
                        break
                    for m in new_materials:
                        yield m
                        emitted += 1
                        if emitted >= max_items:
                            return
            finally:
                browser.close()
