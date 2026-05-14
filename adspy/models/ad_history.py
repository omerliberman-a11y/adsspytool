from datetime import date

from sqlalchemy import Date, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from adspy.models.base import Base


class AdHistory(Base):
    """Daily snapshot per ad — drives the temporal layer (Phase 10).

    One row per (platform, ad_id, snapshot_date). Lets us answer "what changed",
    "when did variant_count cross 5", "is this ad still running".
    """

    __tablename__ = "ad_history"
    __table_args__ = (
        PrimaryKeyConstraint("platform", "ad_id", "snapshot_date", name="pk_ad_history"),
    )

    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    ad_id: Mapped[str] = mapped_column(String(128), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str | None] = mapped_column(String(16))  # active | inactive
    days_active: Mapped[int | None] = mapped_column(Integer)
    variant_count: Mapped[int | None] = mapped_column(Integer)
    winner_score: Mapped[int | None] = mapped_column(Integer)
