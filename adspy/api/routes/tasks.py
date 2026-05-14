from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from adspy.db.session import session_scope
from adspy.models.task import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])

ALLOWED_STATUS = {"queued", "running", "done", "failed", "retrying"}


def _serialize(t: Task) -> dict[str, Any]:
    return {
        "id": t.id,
        "kind": t.kind,
        "status": t.status,
        "priority": t.priority,
        "attempts": t.attempts,
        "max_attempts": t.max_attempts,
        "payload": t.payload,
        "error": t.error,
        "scheduled_for": t.scheduled_for.isoformat(),
        "started_at": t.started_at.isoformat() if t.started_at else None,
        "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        "created_at": t.created_at.isoformat(),
    }


@router.get("")
def list_tasks(
    status: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    if status and status not in ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail=f"status must be one of {ALLOWED_STATUS}")
    stmt = select(Task)
    if status:
        stmt = stmt.where(Task.status == status)
    if kind:
        stmt = stmt.where(Task.kind == kind)
    stmt = stmt.order_by(Task.id.desc()).limit(limit)
    with session_scope() as s:
        rows = list(s.scalars(stmt))
        return {"count": len(rows), "items": [_serialize(t) for t in rows]}


@router.get("/{task_id}")
def get_task(task_id: int) -> dict[str, Any]:
    with session_scope() as s:
        t = s.get(Task, task_id)
        if t is None:
            raise HTTPException(status_code=404, detail="task not found")
        return _serialize(t)
