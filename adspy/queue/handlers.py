"""Task handlers — one per `kind`. Each is registered at import time.

Adding a handler:
    @register_handler("my_kind")
    def my_kind(payload: dict) -> None: ...
"""
from __future__ import annotations

from typing import Any

from adspy.queue.worker import register_handler
from adspy.scrapers.base import ScrapeQuery
from adspy.services.ingestion import ingest_meta
from adspy.utils.logging import get_logger

log = get_logger(__name__)


@register_handler("scrape_meta")
def scrape_meta_handler(payload: dict[str, Any]) -> None:
    query = ScrapeQuery(
        keyword=payload.get("keyword"),
        advertiser_page=payload.get("advertiser_page"),
        countries=tuple(payload.get("countries") or ()),
        active_only=payload.get("active_only", True),
        limit=int(payload.get("limit", 200)),
    )
    result = ingest_meta(query)
    log.info(
        "scrape_meta_done",
        upserted=result.upserted,
        recovered=result.recovered,
        errors=result.errors,
    )


@register_handler("scrape_tiktok")
def scrape_tiktok_handler(payload: dict[str, Any]) -> None:
    from adspy.services.ingestion import ingest_tiktok

    # TikTok Creative Center doesn't support keyword search via this endpoint —
    # it surfaces top ads per (period, country). limit caps total items.
    query = ScrapeQuery(
        keyword="top",  # placeholder; TikTok scraper doesn't use it
        countries=(payload.get("country", "US"),),
        limit=int(payload.get("limit", 50)),
    )
    result = ingest_tiktok(
        query,
        period=int(payload.get("period", 30)),
        country=str(payload.get("country", "US")),
    )
    log.info(
        "scrape_tiktok_done",
        upserted=result.upserted,
        errors=result.errors,
    )


@register_handler("snapshot_replay")
def snapshot_replay_handler(payload: dict[str, Any]) -> None:
    from adspy.scrapers.meta.snapshot_replay import replay_one

    replay_one(ad_id=payload["ad_id"], snapshot_url=payload["snapshot_url"])


@register_handler("analyze_ad")
def analyze_ad_handler(payload: dict[str, Any]) -> None:
    from adspy.ai.analysis import analyze_one

    analyze_one(platform=payload["platform"], ad_id=payload["ad_id"])


@register_handler("embed_ad")
def embed_ad_handler(payload: dict[str, Any]) -> None:
    from adspy.embeddings.embed_ad import embed_one

    embed_one(platform=payload["platform"], ad_id=payload["ad_id"])


@register_handler("daily_snapshot")
def daily_snapshot_handler(payload: dict[str, Any]) -> None:
    from adspy.services.daily_snapshot import run_daily_snapshot

    run_daily_snapshot()


@register_handler("rip_off_scan")
def rip_off_scan_handler(payload: dict[str, Any]) -> None:
    from adspy.services.rip_off import scan_for_rip_offs

    scan_for_rip_offs()


@register_handler("enrich_competitor")
def enrich_competitor_handler(payload: dict[str, Any]) -> None:
    from adspy.services.competitor import enrich_competitor

    enrich_competitor(int(payload["competitor_id"]))


@register_handler("scan_competitor")
def scan_competitor_handler(payload: dict[str, Any]) -> None:
    from adspy.services.competitor import scan_competitor

    scan_competitor(int(payload["competitor_id"]), limit=int(payload.get("limit", 200)))


@register_handler("resolve_link")
def resolve_link_handler(payload: dict[str, Any]) -> None:
    from adspy.services.link_resolver import resolve_for_ad

    resolve_for_ad(platform=payload["platform"], ad_id=payload["ad_id"])


@register_handler("run_due_searches")
def run_due_searches_handler(payload: dict[str, Any]) -> None:
    """Scheduler tick — enqueue all saved searches whose next_run_at has passed."""
    from adspy.services.scheduler import run_due_searches

    n = run_due_searches()
    log.info("scheduler_tick_done", kicked=n)


@register_handler("google_at_discover")
def google_at_discover_handler(payload: dict[str, Any]) -> None:
    """Discover advertisers in Google Ads Transparency by keyword → competitors."""
    from adspy.services.google_discovery import discover_into_competitors

    discover_into_competitors(
        keyword=str(payload["keyword"]),
        limit=int(payload.get("limit", 20)),
        region=int(payload.get("region", 1)),
        min_ad_count=int(payload.get("min_ad_count", 5)),
    )
