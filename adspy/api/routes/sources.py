"""Sources tracking — aggregate link destinations across all ads."""
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from adspy.db.session import session_scope
from adspy.models.ad import Ad

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/domains")
def top_domains(limit: int = Query(default=50, ge=1, le=500)) -> dict[str, Any]:
    """Top destination domains across all resolved ads."""
    with session_scope() as s:
        rows = list(
            s.execute(
                select(
                    Ad.final_domain,
                    func.count().label("ads"),
                    func.count(func.distinct(Ad.advertiser_page_id)).label("advertisers"),
                    func.array_agg(func.distinct(Ad.platform)).label("platforms"),
                )
                .where(Ad.final_domain.is_not(None))
                .group_by(Ad.final_domain)
                .order_by(func.count().desc())
                .limit(limit)
            )
        )
    return {
        "count": len(rows),
        "items": [
            {
                "domain": r.final_domain,
                "ad_count": int(r.ads),
                "advertiser_count": int(r.advertisers),
                "platforms": list(r.platforms or []),
            }
            for r in rows
        ],
    }


@router.get("/affiliate-networks")
def affiliate_networks() -> dict[str, Any]:
    """Affiliate networks detected on resolved links + how many ads use each."""
    with session_scope() as s:
        rows = list(
            s.execute(
                select(Ad.affiliate_network, func.count())
                .where(Ad.affiliate_network.is_not(None))
                .group_by(Ad.affiliate_network)
                .order_by(func.count().desc())
            )
        )
    return {"count": len(rows), "items": [{"network": r[0], "ad_count": int(r[1])} for r in rows]}


@router.get("/by-domain/{domain}")
def ads_for_domain(domain: str, limit: int = Query(default=50, ge=1, le=500)) -> dict[str, Any]:
    """List ads whose final destination matches a given domain."""
    with session_scope() as s:
        rows = list(
            s.scalars(
                select(Ad)
                .where(Ad.final_domain == domain)
                .order_by(Ad.winner_score.desc().nullslast())
                .limit(limit)
            )
        )
        items = [
            {
                "platform": a.platform,
                "ad_id": a.ad_id,
                "advertiser_name": a.advertiser_name,
                "headline": a.headline,
                "winner_score": a.winner_score,
                "media_urls": a.media_urls,
                "source_url": a.source_url,
                "final_url": a.final_url,
            }
            for a in rows
        ]
    return {"domain": domain, "count": len(items), "items": items}
