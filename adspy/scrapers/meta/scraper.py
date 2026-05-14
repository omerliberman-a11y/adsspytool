"""Meta scraper — orchestrates Graph API + (later) snapshot replay.

Phase 0.5: Graph API only. The snapshot-replay worker that fills `media_urls` ships in
Phase 1 (`adspy/scrapers/meta/snapshot_replay.py`).
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from adspy.scrapers.base import ScrapeQuery
from adspy.scrapers.meta.graph_client import MetaGraphClient
from adspy.scrapers.scrape_runner import ScrapeRunner


class MetaScraper:
    def __init__(self, client: MetaGraphClient | None = None) -> None:
        self._client = client

    def scrape(self, query: ScrapeQuery) -> Iterator[dict[str, Any]]:
        run_query = {
            "keyword": query.keyword,
            "advertiser_page": query.advertiser_page,
            "countries": list(query.countries),
            "active_only": query.active_only,
            "limit": query.limit,
        }
        client = self._client or MetaGraphClient()
        with ScrapeRunner(source="meta_graph", platform="meta", query=run_query) as run:
            count = 0
            with client:
                for raw in client.search(query):
                    count += 1
                    yield raw
            run.record(item_count=count, cost_usd=0.0)
