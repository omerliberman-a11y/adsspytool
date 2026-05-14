from typing import Any

from fastapi import APIRouter
from sqlalchemy import select, update

from adspy.analyzers.scoring import score_ad_row
from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.queue.enqueue import enqueue

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/score/recompute")
def recompute_scores() -> dict[str, Any]:
    """Re-score every ad in place (no AI calls)."""
    updated = 0
    with session_scope() as s:
        rows = list(
            s.execute(
                select(
                    Ad.platform,
                    Ad.ad_id,
                    Ad.days_active,
                    Ad.variant_count,
                    Ad.reach_band,
                    Ad.placements,
                    Ad.first_seen,
                )
            )
        )
        for platform, ad_id, days, vc, rb, plac, fs in rows:
            score = score_ad_row(
                {
                    "days_active": days,
                    "variant_count": vc,
                    "reach_band": rb,
                    "placements": list(plac) if plac else None,
                    "first_seen": fs,
                }
            )
            s.execute(
                update(Ad)
                .where(Ad.platform == platform, Ad.ad_id == ad_id)
                .values(winner_score=score)
            )
            updated += 1
    return {"updated": updated}


@router.post("/analyze/batch")
def trigger_analyze_batch(limit: int = 100) -> dict[str, Any]:
    """Enqueue analyze_ad tasks for ads missing ai_summary."""
    n = 0
    with session_scope() as s:
        rows = list(
            s.execute(
                select(Ad.platform, Ad.ad_id).where(Ad.ai_summary.is_(None)).limit(limit)
            )
        )
    for platform, ad_id in rows:
        enqueue("analyze_ad", {"platform": platform, "ad_id": ad_id}, priority=80)
        n += 1
    return {"enqueued": n}


@router.post("/embed/batch")
def trigger_embed_batch(limit: int = 200) -> dict[str, Any]:
    n = 0
    with session_scope() as s:
        rows = list(
            s.execute(
                select(Ad.platform, Ad.ad_id)
                .where(Ad.copy_embedding.is_(None))
                .limit(limit)
            )
        )
    for platform, ad_id in rows:
        enqueue("embed_ad", {"platform": platform, "ad_id": ad_id}, priority=90)
        n += 1
    return {"enqueued": n}


@router.post("/snapshot/batch")
def trigger_snapshot_batch(limit: int = 100) -> dict[str, Any]:
    """Enqueue snapshot_replay for Meta ads missing media_urls."""
    n = 0
    with session_scope() as s:
        rows = list(
            s.execute(
                select(Ad.platform, Ad.ad_id, Ad.landing_url)
                .where(Ad.platform == "meta", Ad.media_urls.is_(None), Ad.landing_url.is_not(None))
                .limit(limit)
            )
        )
    for _, ad_id, url in rows:
        enqueue("snapshot_replay", {"ad_id": ad_id, "snapshot_url": url}, priority=50)
        n += 1
    return {"enqueued": n}


@router.post("/daily-snapshot")
def trigger_daily_snapshot() -> dict[str, Any]:
    task_id = enqueue("daily_snapshot", {}, priority=30)
    return {"task_id": task_id}


@router.post("/rip-off-scan")
def trigger_rip_off_scan() -> dict[str, Any]:
    task_id = enqueue("rip_off_scan", {}, priority=30)
    return {"task_id": task_id}
