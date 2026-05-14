from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from adspy.models.base import Base


class NormalizationFailure(Base):
    __tablename__ = "normalization_failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    classic_error: Mapped[str | None] = mapped_column(Text)
    llm_output: Mapped[str | None] = mapped_column(Text)
    recovered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
