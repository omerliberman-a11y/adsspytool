from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.models.competitor import Competitor
from adspy.queue.enqueue import enqueue
from adspy.services.competitor import create_competitor

router = APIRouter(prefix="/competitors", tags=["competitors"])


class CompetitorCreate(BaseModel):
    domain: str = Field(min_length=3, max_length=255)
    name: str | None = None
    tags: list[str] = Field(default_factory=list)


def _serialize(c: Competitor, ad_count: int | None = None) -> dict[str, Any]:
    return {
        "id": c.id,
        "domain": c.domain,
        "name": c.name,
        "notes": c.notes,
        "tags": c.tags,
        "fb_page_url": c.fb_page_url,
        "fb_page_id": c.fb_page_id,
        "instagram_handle": c.instagram_handle,
        "tiktok_handle": c.tiktok_handle,
        "twitter_handle": c.twitter_handle,
        "youtube_channel": c.youtube_channel,
        "linkedin_company": c.linkedin_company,
        "tech_stack": c.tech_stack,
        "pixels": c.pixels,
        "enabled": c.enabled,
        "scan_interval_hours": c.scan_interval_hours,
        "last_enriched_at": c.last_enriched_at.isoformat() if c.last_enriched_at else None,
        "last_scanned_at": c.last_scanned_at.isoformat() if c.last_scanned_at else None,
        "last_scan_error": c.last_scan_error,
        "ad_count": ad_count,
        "created_at": c.created_at.isoformat(),
    }


@router.get("")
def list_competitors() -> dict[str, Any]:
    with session_scope() as s:
        rows = list(s.scalars(select(Competitor).order_by(Competitor.created_at.desc())))
        counts = dict(
            s.execute(
                select(Ad.competitor_id, func.count())
                .where(Ad.competitor_id.is_not(None))
                .group_by(Ad.competitor_id)
            ).all()
        )
        items = [_serialize(c, ad_count=int(counts.get(c.id, 0))) for c in rows]
    return {"count": len(items), "items": items}


@router.post("", status_code=201)
def add_competitor(req: CompetitorCreate) -> dict[str, Any]:
    competitor_id = create_competitor(req.domain, name=req.name, tags=req.tags)
    enrich_task_id = enqueue(
        "enrich_competitor", {"competitor_id": competitor_id}, priority=40
    )
    return {
        "competitor_id": competitor_id,
        "enrich_task_id": enrich_task_id,
        "note": "Enrichment enqueued. Once fb_page_id resolves, call POST /competitors/{id}/scan.",
    }


@router.get("/{competitor_id}")
def get_competitor(competitor_id: int) -> dict[str, Any]:
    with session_scope() as s:
        c = s.get(Competitor, competitor_id)
        if c is None:
            raise HTTPException(status_code=404, detail="competitor not found")
        ad_count = s.scalar(
            select(func.count()).select_from(Ad).where(Ad.competitor_id == competitor_id)
        ) or 0
        return _serialize(c, ad_count=int(ad_count))


@router.post("/{competitor_id}/enrich")
def trigger_enrich(competitor_id: int) -> dict[str, Any]:
    with session_scope() as s:
        c = s.get(Competitor, competitor_id)
        if c is None:
            raise HTTPException(status_code=404, detail="competitor not found")
    task_id = enqueue("enrich_competitor", {"competitor_id": competitor_id}, priority=40)
    return {"task_id": task_id}


@router.post("/{competitor_id}/scan")
def trigger_scan(competitor_id: int, limit: int = 200) -> dict[str, Any]:
    with session_scope() as s:
        c = s.get(Competitor, competitor_id)
        if c is None:
            raise HTTPException(status_code=404, detail="competitor not found")
        if not c.fb_page_id:
            raise HTTPException(
                status_code=400,
                detail="competitor has no fb_page_id yet — run enrich first",
            )
    task_id = enqueue(
        "scan_competitor", {"competitor_id": competitor_id, "limit": limit}, priority=50
    )
    return {"task_id": task_id}


@router.delete("/{competitor_id}", status_code=204)
def delete_competitor(competitor_id: int) -> None:
    with session_scope() as s:
        c = s.get(Competitor, competitor_id)
        if c is None:
            raise HTTPException(status_code=404, detail="competitor not found")
        s.delete(c)
