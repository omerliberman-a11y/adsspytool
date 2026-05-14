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
    # Chain: enqueue snapshot_replay + analysis tasks for the new ads.
    # We do this from inside ingest_meta in a future iteration; for now just log.


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
