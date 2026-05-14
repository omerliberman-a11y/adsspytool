"""Daily snapshot worker — writes one ad_history row per ad per day.

Run from cron (or `make daily-snapshot`). The temporal layer (advertiser diff,
launch radar, rising-star score) reads this table.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from adspy.analyzers.scoring import score_ad_row
from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.models.ad_history import AdHistory
from adspy.utils.logging import get_logger

log = get_logger(__name__)


def run_daily_snapshot(snapshot_date: date | None = None) -> int:
    """Take a snapshot of every ad. Returns the row count written."""
    today = snapshot_date or datetime.now(UTC).date()
    with session_scope() as s:
        ads = list(
            s.execute(
                select(
                    Ad.platform,
                    Ad.ad_id,
                    Ad.last_seen,
                    Ad.days_active,
                    Ad.variant_count,
                    Ad.first_seen,
                    Ad.reach_band,
                    Ad.placements,
                )
            )
        )

    rows: list[dict[str, object]] = []
    now = datetime.now(UTC)
    for platform, ad_id, last_seen, days_active, variant_count, first_seen, reach_band, plac in ads:
        # active if last_seen is within the past day, otherwise inactive
        status = (
            "active" if last_seen and (now - last_seen).total_seconds() < 60 * 60 * 36
            else "inactive"
        )
        score = score_ad_row(
            {
                "days_active": days_active,
                "variant_count": variant_count,
                "reach_band": reach_band,
                "placements": list(plac) if plac else None,
                "first_seen": first_seen,
            }
        )
        rows.append(
            {
                "platform": platform,
                "ad_id": ad_id,
                "snapshot_date": today,
                "status": status,
                "days_active": days_active,
                "variant_count": variant_count,
                "winner_score": score,
            }
        )

    if not rows:
        log.info("daily_snapshot_no_ads")
        return 0

    with session_scope() as s:
        stmt = insert(AdHistory).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["platform", "ad_id", "snapshot_date"],
            set_={
                "status": stmt.excluded.status,
                "days_active": stmt.excluded.days_active,
                "variant_count": stmt.excluded.variant_count,
                "winner_score": stmt.excluded.winner_score,
            },
        )
        s.execute(stmt)

    log.info("daily_snapshot_done", rows=len(rows), date=str(today))
    return len(rows)
