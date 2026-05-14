from datetime import UTC, datetime, timedelta
from typing import Any

from adspy.db.session import session_scope
from adspy.models.task import Task


def enqueue(
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    priority: int = 100,
    delay_secs: int = 0,
    max_attempts: int = 3,
) -> int:
    """Insert a task. Returns the task id."""
    scheduled_for = datetime.now(UTC) + timedelta(seconds=delay_secs) if delay_secs else None
    task = Task(
        kind=kind,
        payload=payload or {},
        priority=priority,
        max_attempts=max_attempts,
    )
    if scheduled_for:
        task.scheduled_for = scheduled_for
    with session_scope() as s:
        s.add(task)
        s.flush()
        return task.id
