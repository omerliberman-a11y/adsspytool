from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert

from adspy.analyzers.scoring import score_ad_row
from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.normalize import normalize_meta_ad
from adspy.normalize.llm_fallback import recover as llm_recover
from adspy.scrapers.base import ScrapeQuery
from adspy.scrapers.meta import MetaScraper
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


def ingest_meta(query: ScrapeQuery) -> IngestionResult:
    fetched = normalized = recovered = upserted = errors = 0
    rows: list[dict[str, object]] = []

    for raw in MetaScraper().scrape(query):
        fetched += 1
        ad = _normalize_with_fallback(raw)
        if ad is None:
            errors += 1
            continue
        if ad.get("_recovered"):
            recovered += 1
            ad.pop("_recovered", None)
        else:
            normalized += 1
        ad["winner_score"] = score_ad_row(ad)
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
