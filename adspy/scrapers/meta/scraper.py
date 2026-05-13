from collections.abc import Iterator
from typing import Any

from adspy.scrapers.apify_runner import ApifyRunner, RunResult
from adspy.scrapers.base import ScrapeQuery

# Mature Meta Ad Library scraper. See docs/apify_actors.md for the comparison.
META_ACTOR_ID = "apify/facebook-ads-scraper"


class MetaScraper:
    def __init__(self, runner: ApifyRunner | None = None) -> None:
        self.runner = runner or ApifyRunner()

    def scrape(self, query: ScrapeQuery) -> tuple[RunResult, Iterator[dict[str, Any]]]:
        run_input = self._build_input(query)
        result = self.runner.run(
            actor_id=META_ACTOR_ID,
            platform="meta",
            run_input=run_input,
        )
        return result, self.runner.iter_dataset(result.dataset_id)

    @staticmethod
    def _build_input(query: ScrapeQuery) -> dict[str, Any]:
        urls: list[str] = []
        countries = list(query.countries) or ["US"]
        active_status = "active" if query.active_only else "all"

        if query.keyword:
            for country in countries:
                urls.append(
                    "https://www.facebook.com/ads/library/"
                    f"?active_status={active_status}"
                    "&ad_type=all"
                    f"&country={country}"
                    f"&q={query.keyword}"
                    "&search_type=keyword_unordered"
                )
        if query.advertiser_page:
            for country in countries:
                urls.append(
                    "https://www.facebook.com/ads/library/"
                    f"?active_status={active_status}"
                    "&ad_type=all"
                    f"&country={country}"
                    f"&view_all_page_id={query.advertiser_page}"
                )

        return {
            "startUrls": [{"url": u} for u in urls],
            "resultsLimit": query.limit,
            "activeStatus": active_status,
        }
