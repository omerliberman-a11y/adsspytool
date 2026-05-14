from datetime import date, datetime

from sqlalchemy import ARRAY, Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from adspy.models.base import Base


class Competitor(Base):
    """A tracked competitor — keyed by primary domain.

    Enrichment extracts social handles + tech stack from the homepage.
    The scan worker uses `fb_page_id` (resolved during enrichment) to hit the
    Meta Graph API and ingest the competitor's ads, tagged with `competitor_id`.
    """

    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Social handles discovered from the homepage
    fb_page_url: Mapped[str | None] = mapped_column(Text)
    fb_page_id: Mapped[str | None] = mapped_column(String(64), index=True)
    instagram_handle: Mapped[str | None] = mapped_column(String(64))
    tiktok_handle: Mapped[str | None] = mapped_column(String(64))
    twitter_handle: Mapped[str | None] = mapped_column(String(64))
    youtube_channel: Mapped[str | None] = mapped_column(String(255))
    linkedin_company: Mapped[str | None] = mapped_column(String(255))

    # Tech-stack fingerprint
    tech_stack: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    pixels: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # WHOIS / DNS (filled by a later phase; nullable now)
    domain_created_at: Mapped[date | None] = mapped_column(Date)

    # Scan management
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scan_interval_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    last_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_scan_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
