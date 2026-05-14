from typing import Any

from fastapi import APIRouter
from sqlalchemy import case, func, select

from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.models.ai_call import AICall
from adspy.models.scrape_run import ScrapeRun
from adspy.models.task import Task

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def stats() -> dict[str, Any]:
    with session_scope() as s:
        total = s.scalar(select(func.count()).select_from(Ad)) or 0
        per_platform = dict(
            s.execute(select(Ad.platform, func.count()).group_by(Ad.platform)).all()
        )
        per_creative_type = dict(
            s.execute(
                select(Ad.creative_type, func.count()).group_by(Ad.creative_type)
            ).all()
        )
        per_hook_type = dict(
            s.execute(select(Ad.hook_type, func.count()).group_by(Ad.hook_type)).all()
        )
        score_buckets_stmt = select(
            func.count(case((Ad.winner_score >= 80, 1))).label("ge_80"),
            func.count(case((Ad.winner_score >= 60, 1))).label("ge_60"),
            func.count(case((Ad.winner_score >= 40, 1))).label("ge_40"),
            func.count(case((Ad.winner_score >= 0, 1))).label("ge_0"),
        )
        buckets = s.execute(score_buckets_stmt).one()._asdict()

        ai_calls_today = (
            s.scalar(
                select(func.count())
                .select_from(AICall)
                .where(AICall.created_at >= func.current_date())
            )
            or 0
        )
        ai_by_provider = dict(
            s.execute(
                select(AICall.provider, func.count())
                .where(AICall.created_at >= func.current_date())
                .group_by(AICall.provider)
            ).all()
        )

        scrape_runs_today = (
            s.scalar(
                select(func.count())
                .select_from(ScrapeRun)
                .where(ScrapeRun.started_at >= func.current_date())
            )
            or 0
        )

        tasks_by_status = dict(
            s.execute(select(Task.status, func.count()).group_by(Task.status)).all()
        )

    return {
        "ads": {
            "total": total,
            "per_platform": per_platform,
            "per_creative_type": per_creative_type,
            "per_hook_type": per_hook_type,
            "winner_score_buckets": buckets,
        },
        "ai_today": {"total": ai_calls_today, "per_provider": ai_by_provider},
        "scrape_runs_today": scrape_runs_today,
        "tasks_by_status": tasks_by_status,
    }
