"""Meta Ad Library Graph API client.

Endpoint: GET https://graph.facebook.com/{version}/ads_archive

Free, official, no rate dance required. Documented at:
https://www.facebook.com/ads/library/api/
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from adspy.config import Settings, get_settings
from adspy.scrapers.base import ScrapeQuery
from adspy.utils.errors import ScrapeError
from adspy.utils.logging import get_logger

log = get_logger(__name__)

DEFAULT_FIELDS = ",".join(
    [
        "id",
        "ad_creative_bodies",
        "ad_creative_link_captions",
        "ad_creative_link_descriptions",
        "ad_creative_link_titles",
        "ad_delivery_start_time",
        "ad_delivery_stop_time",
        "ad_snapshot_url",
        "bylines",
        "currency",
        "delivery_by_region",
        "demographic_distribution",
        "estimated_audience_size",
        "eu_total_reach",
        "impressions",
        "languages",
        "page_id",
        "page_name",
        "publisher_platforms",
        "spend",
        "target_ages",
        "target_gender",
        "target_locations",
    ]
)


class MetaGraphClient:
    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        token = self.settings.meta_graph_token.get_secret_value()
        if not token:
            raise ScrapeError("META_GRAPH_TOKEN is not configured")
        self._token = token
        self._base = (
            f"https://graph.facebook.com/{self.settings.meta_graph_api_version}/ads_archive"
        )
        self._client = client or httpx.Client(timeout=self.settings.scrape_timeout_secs)

    def __enter__(self) -> MetaGraphClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self._client.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "access_token": self._token}
        r = self._client.get(self._base, params=params)
        if r.status_code == 400:
            raise ScrapeError(f"Graph API 400: {r.text}")
        r.raise_for_status()
        return r.json()  # type: ignore[no-any-return]

    def search(self, query: ScrapeQuery) -> Iterator[dict[str, Any]]:
        """Yield raw ad records page-by-page, capped at settings.scrape_max_items_per_run."""
        if not query.keyword and not query.advertiser_page:
            raise ScrapeError("Meta scrape requires either keyword or advertiser_page")
        params: dict[str, Any] = {
            "ad_type": "ALL",
            "ad_active_status": "ACTIVE" if query.active_only else "ALL",
            "fields": DEFAULT_FIELDS,
            "limit": min(query.limit, 200),
        }
        countries = list(query.countries) or ["US"]
        params["ad_reached_countries"] = _bracket(countries)
        if query.keyword:
            params["search_terms"] = query.keyword
        if query.advertiser_page:
            params["search_page_ids"] = _bracket([query.advertiser_page])

        emitted = 0
        cap = self.settings.scrape_max_items_per_run
        while True:
            payload = self._get(params)
            for item in payload.get("data", []):
                yield item
                emitted += 1
                if emitted >= cap:
                    log.warning("meta_graph_cap_reached", cap=cap)
                    return
            next_url = payload.get("paging", {}).get("next")
            after = payload.get("paging", {}).get("cursors", {}).get("after")
            if not next_url or not after:
                return
            params = {**params, "after": after}


def _bracket(values: list[str]) -> str:
    """Graph API wants array params as JSON-ish strings: ['US','CA']."""
    inner = ",".join(f'"{v}"' for v in values)
    return f"[{inner}]"
