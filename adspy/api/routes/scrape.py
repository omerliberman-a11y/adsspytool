from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from adspy.queue.enqueue import enqueue

router = APIRouter(prefix="/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    keyword: str | None = None
    advertiser_page: str | None = None
    countries: list[str] = Field(default_factory=list)
    active_only: bool = True
    limit: int = Field(default=200, ge=1, le=2000)


@router.post("/meta")
def scrape_meta(req: ScrapeRequest) -> dict[str, Any]:
    payload = {
        "keyword": req.keyword,
        "advertiser_page": req.advertiser_page,
        "countries": req.countries,
        "active_only": req.active_only,
        "limit": req.limit,
    }
    task_id = enqueue("scrape_meta", payload, priority=50)
    return {"task_id": task_id, "kind": "scrape_meta", "status": "queued"}
