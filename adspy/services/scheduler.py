"""Saved-search scheduler.

`run_due_searches` scans `saved_searches`, enqueues the matching scrape task
for each one whose `next_run_at` has passed, and bumps `next_run_at` forward
by `interval_minutes`. Designed to run frequently (every minute) — cheap, idempotent.

Wiring:
  - Operator creates a SavedSearch row (e.g. "Cold plunge — TikTok US daily")
  - A periodic `run_due_searches` task runs the loop
  - The first invocation enqueues the first scrape immediately (next_run_at
    defaults to now())
  - On success, last_task_id is recorded and next_run_at slides forward
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from adspy.db.session import session_scope
from adspy.models.saved_search import SavedSearch
from adspy.queue.enqueue import enqueue
from adspy.utils.logging import get_logger

log = get_logger(__name__)


def run_due_searches() -> int:
    """Enqueue scrape tasks for every saved-search whose next_run_at has passed.

    Returns count of searches kicked.
    """
    now = datetime.now(UTC)
    kicked = 0
    with session_scope() as s:
        due = list(
            s.scalars(
                select(SavedSearch)
                .where(SavedSearch.enabled.is_(True))
                .where(SavedSearch.next_run_at <= now)
                .order_by(SavedSearch.next_run_at)
            )
        )
        for ss in due:
            try:
                task_id = enqueue(ss.task_kind, ss.params or {}, priority=60)
                ss.last_task_id = task_id
                ss.last_run_at = now
                ss.last_error = None
                ss.next_run_at = now + timedelta(minutes=ss.interval_minutes)
                kicked += 1
                log.info(
                    "saved_search_fired",
                    id=ss.id,
                    name=ss.name,
                    task_id=task_id,
                    next_run_at=ss.next_run_at.isoformat(),
                )
            except Exception as exc:  # noqa: BLE001
                ss.last_error = f"{type(exc).__name__}: {exc}"[:500]
                log.error("saved_search_enqueue_failed", id=ss.id, error=str(exc))
    return kicked
