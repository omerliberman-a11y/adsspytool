"""Worker loop. Pulls tasks via SELECT ... FOR UPDATE SKIP LOCKED, dispatches by kind.

Usage: `python -m adspy.queue.worker` (or `make worker`).

The handler registry is populated by `adspy.queue.handlers` at import time. Add
new handlers by decorating with `@register_handler("kind_name")`.
"""
from __future__ import annotations

import signal
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from adspy.db.session import session_scope
from adspy.models.task import Task
from adspy.utils.logging import configure_logging, get_logger

log = get_logger(__name__)

Handler = Callable[[dict[str, Any]], None]
_REGISTRY: dict[str, Handler] = {}


def register_handler(kind: str) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        if kind in _REGISTRY:
            raise RuntimeError(f"Handler '{kind}' already registered")
        _REGISTRY[kind] = fn
        return fn

    return deco


class Worker:
    def __init__(self, poll_interval: float = 2.0) -> None:
        self.poll_interval = poll_interval
        self._stop = False
        # eager-import handlers so the registry is populated
        import adspy.queue.handlers  # noqa: F401

    def stop(self, *_: object) -> None:
        log.info("worker_shutdown_requested")
        self._stop = True

    def run(self) -> None:
        configure_logging()
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        log.info("worker_started", handlers=sorted(_REGISTRY.keys()))
        while not self._stop:
            task = self._claim_next()
            if task is None:
                time.sleep(self.poll_interval)
                continue
            self._dispatch(task)
        log.info("worker_stopped")

    def _claim_next(self) -> Task | None:
        with session_scope() as s:
            row = s.execute(
                text(
                    """
                    SELECT id FROM tasks
                    WHERE status IN ('queued', 'retrying')
                      AND scheduled_for <= now()
                      AND kind = ANY(:kinds)
                    ORDER BY priority ASC, scheduled_for ASC, id ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                ),
                {"kinds": list(_REGISTRY.keys())},
            ).first()
            if row is None:
                return None
            task = s.get(Task, row[0])
            assert task is not None
            task.status = "running"
            task.attempts += 1
            task.started_at = datetime.now(UTC)
            s.flush()
            s.expunge(task)
            return task

    def _dispatch(self, task: Task) -> None:
        handler = _REGISTRY.get(task.kind)
        if handler is None:
            self._finalize(task, status="failed", error=f"no handler for '{task.kind}'")
            return
        try:
            handler(task.payload or {})
            self._finalize(task, status="done")
        except Exception as exc:  # noqa: BLE001
            log.error("task_failed", kind=task.kind, id=task.id, error=str(exc))
            self._finalize(
                task,
                status="retrying" if task.attempts < task.max_attempts else "failed",
                error=str(exc)[:2000],
            )

    @staticmethod
    def _finalize(task: Task, *, status: str, error: str | None = None) -> None:
        with session_scope() as s:
            row = s.get(Task, task.id)
            if row is None:
                return
            row.status = status
            row.error = error
            row.finished_at = datetime.now(UTC) if status in ("done", "failed") else None


def _drain_session(_: Session) -> None:  # pragma: no cover — type-hint helper for tests
    pass


def main() -> None:  # pragma: no cover
    Worker().run()


if __name__ == "__main__":  # pragma: no cover
    main()
