"""Similarity endpoints: 'more like this' via pgvector cosine distance."""
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from adspy.db.session import session_scope
from adspy.models.ad import Ad

router = APIRouter(prefix="/similar", tags=["similar"])


def _summary(a: Ad, distance: float | None = None) -> dict[str, Any]:
    return {
        "platform": a.platform,
        "ad_id": a.ad_id,
        "advertiser_name": a.advertiser_name,
        "headline": a.headline,
        "primary_text": (a.primary_text or "")[:200],
        "creative_type": a.creative_type,
        "winner_score": a.winner_score,
        "hook_type": a.hook_type,
        "media_urls": a.media_urls,
        "distance": distance,
    }


@router.get("/{platform}/{ad_id}")
def similar(
    platform: str,
    ad_id: str,
    by: str = Query(default="copy", regex="^(copy|image)$"),
    limit: int = Query(default=12, ge=1, le=100),
) -> dict[str, Any]:
    with session_scope() as s:
        anchor = s.get(Ad, (platform, ad_id))
        if anchor is None:
            raise HTTPException(status_code=404, detail="anchor ad not found")
        vector_col = Ad.copy_embedding if by == "copy" else Ad.image_embedding
        anchor_vec = anchor.copy_embedding if by == "copy" else anchor.image_embedding
        if anchor_vec is None:
            raise HTTPException(
                status_code=400, detail=f"anchor ad has no {by}_embedding (run embed_ad)"
            )

        distance = vector_col.cosine_distance(anchor_vec)
        stmt = (
            select(Ad, distance.label("d"))
            .where(vector_col.is_not(None))
            .where(~((Ad.platform == platform) & (Ad.ad_id == ad_id)))
            .order_by("d")
            .limit(limit)
        )
        rows = list(s.execute(stmt))
        return {
            "anchor": _summary(anchor),
            "by": by,
            "items": [_summary(ad, distance=float(d)) for ad, d in rows],
        }
