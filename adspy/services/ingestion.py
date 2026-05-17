from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert

from adspy.analyzers.scoring import score_ad_row
from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.normalize import normalize_meta_ad, normalize_tiktok_ad
from adspy.normalize.llm_fallback import recover as llm_recover
from adspy.queue.enqueue import enqueue
from adspy.scrapers.base import ScrapeQuery
from adspy.scrapers.meta import MetaScraper
from adspy.scrapers.tiktok import TikTokScraper
from adspy.services.competitor import auto_link_ad_to_competitor
from adspy.utils.errors import NormalizerError
from adspy.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class IngestionResult:
    platform: str
    fetched: int
    normalized: int
    recovered: int
    upserted: int
    errors: int


def ingest_meta(query: ScrapeQuery, *, enqueue_followups: bool = True) -> IngestionResult:
    fetched = normalized = recovered = upserted = errors = 0
    rows: list[dict[str, object]] = []

    for raw in MetaScraper().scrape(query):
        fetched += 1
        ad = _normalize_with_fallback(raw)
        if ad is None:
            errors += 1
            continue
        if ad.pop("_recovered", False):
            recovered += 1
        else:
            normalized += 1
        ad["winner_score"] = score_ad_row(ad)
        ad["competitor_id"] = auto_link_ad_to_competitor(ad)
        ad["updated_at"] = datetime.now(UTC)
        rows.append(ad)

    if rows:
        with session_scope() as s:
            stmt = insert(Ad).values(rows)
            update_cols = {
                c.name: getattr(stmt.excluded, c.name)
                for c in Ad.__table__.columns
                if c.name not in ("platform", "ad_id", "created_at")
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=["platform", "ad_id"], set_=update_cols
            )
            s.execute(stmt)
            upserted = len(rows)

    if enqueue_followups and rows:
        _enqueue_followups(rows)

    log.info(
        "meta_ingest_done",
        fetched=fetched,
        normalized=normalized,
        recovered=recovered,
        upserted=upserted,
        errors=errors,
    )
    return IngestionResult(
        platform="meta",
        fetched=fetched,
        normalized=normalized,
        recovered=recovered,
        upserted=upserted,
        errors=errors,
    )


def _normalize_with_fallback(raw: dict) -> dict | None:
    try:
        return normalize_meta_ad(raw)
    except NormalizerError as exc:
        log.warning("normalize_classic_failed", error=str(exc))
        rescued = llm_recover("meta", raw, classic_error=exc)
        if rescued is None:
            return None
        rescued["_recovered"] = True
        return rescued


def _enqueue_followups(rows: list[dict[str, object]]) -> None:
    """For each newly-ingested ad, enqueue the downstream pipeline tasks."""
    for ad in rows:
        ad_id = ad.get("ad_id")
        platform = str(ad.get("platform") or "meta")
        snapshot_url = ad.get("landing_url")
        if not isinstance(ad_id, str):
            continue
        if platform == "meta" and isinstance(snapshot_url, str) and not ad.get("media_urls"):
            enqueue("snapshot_replay", {"ad_id": ad_id, "snapshot_url": snapshot_url}, priority=50)
        enqueue("analyze_ad", {"platform": platform, "ad_id": ad_id}, priority=80)
        enqueue("embed_ad", {"platform": platform, "ad_id": ad_id}, priority=90)


def ingest_tiktok(
    query: ScrapeQuery,
    *,
    period: int = 30,
    country: str = "US",
    enqueue_followups: bool = True,
) -> IngestionResult:
    fetched = normalized = upserted = errors = 0
    rows: list[dict[str, object]] = []

    scraper = TikTokScraper(period=period, country=country)
    for raw in scraper.scrape(query):
        fetched += 1
        try:
            ad = normalize_tiktok_ad(raw)
        except NormalizerError as exc:
            log.warning("tiktok_normalize_failed", error=str(exc))
            errors += 1
            continue
        normalized += 1
        ad["winner_score"] = score_ad_row(ad)
        ad["competitor_id"] = auto_link_ad_to_competitor(ad)
        ad["updated_at"] = datetime.now(UTC)
        rows.append(ad)

    if rows:
        with session_scope() as s:
            stmt = insert(Ad).values(rows)
            update_cols = {
                c.name: getattr(stmt.excluded, c.name)
                for c in Ad.__table__.columns
                if c.name not in ("platform", "ad_id", "created_at")
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=["platform", "ad_id"], set_=update_cols
            )
            s.execute(stmt)
            upserted = len(rows)

    if enqueue_followups and rows:
        _enqueue_followups(rows)

    log.info(
        "tiktok_ingest_done",
        fetched=fetched,
        normalized=normalized,
        upserted=upserted,
        errors=errors,
        country=country,
        period=period,
    )
    return IngestionResult(
        platform="tiktok",
        fetched=fetched,
        normalized=normalized,
        recovered=0,
        upserted=upserted,
        errors=errors,
    )
