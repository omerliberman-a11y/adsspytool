from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from adspy.queue.enqueue import enqueue

router = APIRouter(prefix="/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    keyword: str | None = None
    advertiser_page: str | None = None
    countries: list[str] = Field(default_factory=list)
    publisher_platforms: list[str] = Field(
        default_factory=list,
        description="Scope to specific surfaces, e.g. ['instagram'], ['facebook','instagram']. Empty = all.",
    )
    active_only: bool = True
    limit: int = Field(default=200, ge=1, le=2000)


@router.post("/meta")
def scrape_meta(req: ScrapeRequest) -> dict[str, Any]:
    payload = {
        "keyword": req.keyword,
        "advertiser_page": req.advertiser_page,
        "countries": req.countries,
        "publisher_platforms": req.publisher_platforms,
        "active_only": req.active_only,
        "limit": req.limit,
    }
    task_id = enqueue("scrape_meta", payload, priority=50)
    return {"task_id": task_id, "kind": "scrape_meta", "status": "queued"}


@router.post("/instagram")
def scrape_instagram(req: ScrapeRequest) -> dict[str, Any]:
    """Convenience wrapper for Meta scrape scoped to Instagram only."""
    payload = {
        "keyword": req.keyword,
        "advertiser_page": req.advertiser_page,
        "countries": req.countries,
        "publisher_platforms": ["instagram"],
        "active_only": req.active_only,
        "limit": req.limit,
    }
    task_id = enqueue("scrape_meta", payload, priority=50)
    return {"task_id": task_id, "kind": "scrape_meta", "platform_scope": "instagram"}


class TikTokScrapeRequest(BaseModel):
    country: str = Field(default="US", min_length=2, max_length=4)
    period: int = Field(default=30, ge=7, le=120)  # 7, 30, or 120
    limit: int = Field(default=50, ge=1, le=200)


@router.post("/tiktok")
def scrape_tiktok(req: TikTokScrapeRequest) -> dict[str, Any]:
    # Snap period to one of TikTok's allowed values.
    period = min((7, 30, 120), key=lambda v: abs(v - req.period))
    payload = {
        "country": req.country.upper(),
        "period": period,
        "limit": req.limit,
    }
    task_id = enqueue("scrape_tiktok", payload, priority=50)
    return {"task_id": task_id, "kind": "scrape_tiktok", "status": "queued"}
