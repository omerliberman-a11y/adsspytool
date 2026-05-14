from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from adspy.models.base import Base


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    query_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    cost_usd: Mapped[float | None] = mapped_column(Float)
    duration_secs: Mapped[float | None] = mapped_column(Float)
    item_count: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
