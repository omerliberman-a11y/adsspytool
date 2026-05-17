from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from adspy.models.base import Base


class SavedSearch(Base):
    """A recurring scrape configuration.

    The scheduler worker enqueues the matching scrape_<platform> task whenever
    `next_run_at` is in the past and `enabled` is true, then resets
    `next_run_at = now() + interval_minutes`.
    """

    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    # task kind to enqueue (scrape_meta | scrape_tiktok | ...)
    task_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    # payload passed straight to the task handler
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1440)

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_task_id: Mapped[int | None] = mapped_column(Integer)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()", index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
