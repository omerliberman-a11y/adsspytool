from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from adspy.db.session import session_scope
from adspy.models.saved_search import SavedSearch
from adspy.queue.enqueue import enqueue
from adspy.services.scheduler import run_due_searches

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


ALLOWED_KINDS = {"scrape_meta", "scrape_tiktok"}


class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    platform: str = Field(min_length=2, max_length=32)
    task_kind: str
    params: dict[str, Any] = Field(default_factory=dict)
    interval_minutes: int = Field(default=1440, ge=15, le=24 * 60 * 7)
    enabled: bool = True


class SavedSearchUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=15, le=24 * 60 * 7)
    params: dict[str, Any] | None = None


def _serialize(s: SavedSearch) -> dict[str, Any]:
    return {
        "id": s.id,
        "name": s.name,
        "platform": s.platform,
        "task_kind": s.task_kind,
        "params": s.params,
        "enabled": s.enabled,
        "interval_minutes": s.interval_minutes,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "last_task_id": s.last_task_id,
        "last_error": s.last_error,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
        "created_at": s.created_at.isoformat(),
    }


@router.get("")
def list_searches() -> dict[str, Any]:
    with session_scope() as s:
        rows = list(s.scalars(select(SavedSearch).order_by(SavedSearch.created_at.desc())))
        return {"count": len(rows), "items": [_serialize(r) for r in rows]}


@router.post("", status_code=201)
def create_search(req: SavedSearchCreate) -> dict[str, Any]:
    if req.task_kind not in ALLOWED_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"task_kind must be one of {sorted(ALLOWED_KINDS)}",
        )
    with session_scope() as s:
        row = SavedSearch(
            name=req.name,
            platform=req.platform,
            task_kind=req.task_kind,
            params=req.params,
            interval_minutes=req.interval_minutes,
            enabled=req.enabled,
            next_run_at=datetime.now(UTC),  # fire immediately on next scheduler tick
        )
        s.add(row)
        s.flush()
        return _serialize(row)


@router.patch("/{search_id}")
def update_search(search_id: int, req: SavedSearchUpdate) -> dict[str, Any]:
    with session_scope() as s:
        row = s.get(SavedSearch, search_id)
        if row is None:
            raise HTTPException(status_code=404, detail="saved_search not found")
        if req.name is not None:
            row.name = req.name
        if req.enabled is not None:
            row.enabled = req.enabled
        if req.interval_minutes is not None:
            row.interval_minutes = req.interval_minutes
        if req.params is not None:
            row.params = req.params
        return _serialize(row)


@router.delete("/{search_id}", status_code=204)
def delete_search(search_id: int) -> None:
    with session_scope() as s:
        row = s.get(SavedSearch, search_id)
        if row is None:
            raise HTTPException(status_code=404, detail="saved_search not found")
        s.delete(row)


@router.post("/{search_id}/run-now")
def run_now(search_id: int) -> dict[str, Any]:
    """Force-fire a single saved search regardless of next_run_at."""
    with session_scope() as s:
        row = s.get(SavedSearch, search_id)
        if row is None:
            raise HTTPException(status_code=404, detail="saved_search not found")
        task_id = enqueue(row.task_kind, row.params or {}, priority=60)
        row.last_task_id = task_id
        row.last_run_at = datetime.now(UTC)
        return {"task_id": task_id, "saved_search_id": search_id}


@router.post("/scheduler/tick")
def trigger_scheduler_tick() -> dict[str, Any]:
    """Force a scheduler scan now (normally runs every 60s inside the worker)."""
    n = run_due_searches()
    return {"kicked": n}
