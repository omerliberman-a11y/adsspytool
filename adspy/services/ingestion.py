from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert

from adspy.analyzers.scoring import score_ad_row
from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.scrapers.base import ScrapeQuery
from adspy.scrapers.meta import MetaScraper, normalize_meta_ad
from adspy.utils.errors import NormalizerError
from adspy.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class IngestionResult:
    platform: str
    fetched: int
    normalized: int
    upserted: int
    scored: int
    errors: int


def ingest_meta(query: ScrapeQuery) -> IngestionResult:
    scraper = MetaScraper()
    run, items = scraper.scrape(query)

    fetched = normalized = upserted = scored = errors = 0
    rows: list[dict[str, object]] = []

    for raw in items:
        fetched += 1
        try:
            ad = normalize_meta_ad(raw)
            normalized += 1
        except NormalizerError as exc:
            log.warning("normalize_failed", error=str(exc))
            errors += 1
            continue
        ad["winner_score"] = score_ad_row(ad)
        scored += 1
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

    log.info(
        "meta_ingest_done",
        run_id=run.run_id,
        fetched=fetched,
        normalized=normalized,
        upserted=upserted,
        errors=errors,
    )
    return IngestionResult(
        platform="meta",
        fetched=fetched,
        normalized=normalized,
        upserted=upserted,
        scored=scored,
        errors=errors,
    )
