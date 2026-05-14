"""ScrapeRun row-writer. Wraps any scrape with observability + cost-cap accounting.

Every scrape (Graph API, capture-replay, public CSV) writes one row in `scrape_runs`.
Use as a context manager:

    with ScrapeRunner(source="meta_graph", platform="meta", query={"keyword": "..."}) as run:
        items = list(do_the_scrape())
        run.record(item_count=len(items))
"""
from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

from adspy.db.session import session_scope
from adspy.models.scrape_run import ScrapeRun
from adspy.utils.logging import get_logger

log = get_logger(__name__)


class ScrapeRunner(AbstractContextManager["ScrapeRunner"]):
    def __init__(self, *, source: str, platform: str, query: dict[str, Any]) -> None:
        self.source = source
        self.platform = platform
        self.query = query
        self._record_id: int | None = None
        self._started: datetime | None = None
        self._item_count: int = 0
        self._cost_usd: float = 0.0

    def __enter__(self) -> ScrapeRunner:
        self._started = datetime.now(UTC)
        record = ScrapeRun(
            source=self.source,
            platform=self.platform,
            query_json=self.query,
            status="running",
            started_at=self._started,
        )
        with session_scope() as s:
            s.add(record)
            s.flush()
            self._record_id = record.id
        return self

    def record(self, *, item_count: int, cost_usd: float = 0.0) -> None:
        self._item_count = item_count
        self._cost_usd = cost_usd

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._record_id is None or self._started is None:
            return
        duration = (datetime.now(UTC) - self._started).total_seconds()
        with session_scope() as s:
            row = s.get(ScrapeRun, self._record_id)
            if row is None:
                return
            if exc is None:
                row.status = "ok"
                row.item_count = self._item_count
                row.cost_usd = self._cost_usd
            else:
                row.status = "error"
                row.error_message = f"{type(exc).__name__}: {exc}"[:1000]
            row.duration_secs = duration
            row.finished_at = datetime.now(UTC)
        if exc is None:
            log.info(
                "scrape_run_ok",
                source=self.source,
                platform=self.platform,
                items=self._item_count,
                cost=self._cost_usd,
                seconds=round(duration, 1),
            )
        else:
            log.error(
                "scrape_run_error",
                source=self.source,
                platform=self.platform,
                error=str(exc),
                seconds=round(duration, 1),
            )
