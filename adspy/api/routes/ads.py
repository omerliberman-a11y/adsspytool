from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from adspy.db.session import session_scope
from adspy.models.ad import Ad

router = APIRouter(prefix="/ads", tags=["ads"])

ALLOWED_PLATFORMS = {"meta", "x", "tiktok", "google", "linkedin"}


def _serialize(a: Ad) -> dict[str, Any]:
    return {
        "platform": a.platform,
        "ad_id": a.ad_id,
        "advertiser_name": a.advertiser_name,
        "advertiser_page_id": a.advertiser_page_id,
        "advertiser_url": a.advertiser_url,
        "first_seen": a.first_seen.isoformat() if a.first_seen else None,
        "last_seen": a.last_seen.isoformat() if a.last_seen else None,
        "days_active": a.days_active,
        "countries": a.countries,
        "languages": a.languages,
        "placements": a.placements,
        "creative_type": a.creative_type,
        "media_urls": a.media_urls,
        "headline": a.headline,
        "primary_text": a.primary_text,
        "description": a.description,
        "cta_text": a.cta_text,
        "cta_url": a.cta_url,
        "landing_url": a.landing_url,
        "variant_count": a.variant_count,
        "reach_band": a.reach_band,
        "winner_score": a.winner_score,
        "rising_star_score": a.rising_star_score,
        "hook_type": a.hook_type,
        "awareness_stage": a.awareness_stage,
        "copy_framework": a.copy_framework,
        "ai_hook": a.ai_hook,
        "ai_angle": a.ai_angle,
        "ai_offer": a.ai_offer,
        "ai_summary": a.ai_summary,
        "ai_rewritten_copy": a.ai_rewritten_copy,
        "source_url": a.source_url,
        "link_chain": a.link_chain,
        "final_url": a.final_url,
        "final_domain": a.final_domain,
        "affiliate_network": a.affiliate_network,
        "link_resolved_at": a.link_resolved_at.isoformat() if a.link_resolved_at else None,
    }


@router.get("")
def list_ads(
    platform: str | None = Query(default=None),
    min_score: int = Query(default=0, ge=0, le=100),
    days_active_gte: int | None = Query(default=None, ge=0),
    country: str | None = Query(default=None, min_length=2, max_length=8),
    creative_type: str | None = Query(default=None),
    hook_type: str | None = Query(default=None),
    awareness_stage: int | None = Query(default=None, ge=1, le=5),
    copy_framework: str | None = Query(default=None),
    advertiser_page_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    if platform and platform not in ALLOWED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"platform must be one of {ALLOWED_PLATFORMS}")

    stmt = select(Ad)
    if platform:
        stmt = stmt.where(Ad.platform == platform)
    if min_score > 0:
        stmt = stmt.where(Ad.winner_score >= min_score)
    if days_active_gte is not None:
        stmt = stmt.where(Ad.days_active >= days_active_gte)
    if country:
        stmt = stmt.where(Ad.countries.any(country.upper()))
    if creative_type:
        stmt = stmt.where(Ad.creative_type == creative_type)
    if hook_type:
        stmt = stmt.where(Ad.hook_type == hook_type)
    if awareness_stage is not None:
        stmt = stmt.where(Ad.awareness_stage == awareness_stage)
    if copy_framework:
        stmt = stmt.where(Ad.copy_framework == copy_framework)
    if advertiser_page_id:
        stmt = stmt.where(Ad.advertiser_page_id == advertiser_page_id)
    stmt = stmt.order_by(Ad.winner_score.desc().nullslast()).limit(limit).offset(offset)

    with session_scope() as s:
        rows = list(s.scalars(stmt))
        return {"count": len(rows), "items": [_serialize(a) for a in rows]}


@router.get("/{platform}/{ad_id}")
def get_ad(platform: str, ad_id: str) -> dict[str, Any]:
    if platform not in ALLOWED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"platform must be one of {ALLOWED_PLATFORMS}")
    with session_scope() as s:
        ad = s.get(Ad, (platform, ad_id))
        if ad is None:
            raise HTTPException(status_code=404, detail="ad not found")
        return _serialize(ad)
