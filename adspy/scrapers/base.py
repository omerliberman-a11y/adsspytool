from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScrapeQuery:
    """Generic scrape request. Field applicability is per-scraper.

    Meta requires keyword or advertiser_page; TikTok ignores both and scrapes
    top-N per (country, period). Per-scraper validation lives in each scraper.
    """

    keyword: str | None = None
    advertiser_page: str | None = None
    countries: tuple[str, ...] = field(default_factory=tuple)
    publisher_platforms: tuple[str, ...] = field(default_factory=tuple)
    active_only: bool = True
    limit: int = 200
