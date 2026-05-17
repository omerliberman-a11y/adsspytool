from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from adspy.models.base import Base


class Ad(Base):
    __tablename__ = "ads"
    __table_args__ = (PrimaryKeyConstraint("platform", "ad_id", name="pk_ads"),)

    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    ad_id: Mapped[str] = mapped_column(String(128), nullable=False)

    advertiser_name: Mapped[str | None] = mapped_column(Text)
    advertiser_page_id: Mapped[str | None] = mapped_column(String(128))
    advertiser_url: Mapped[str | None] = mapped_column(Text)

    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    days_active: Mapped[int | None] = mapped_column(Integer)

    countries: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    languages: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    placements: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    creative_type: Mapped[str | None] = mapped_column(String(16))
    media_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    media_phash: Mapped[list[str] | None] = mapped_column(ARRAY(String(32)))
    local_media_paths: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    headline: Mapped[str | None] = mapped_column(Text)
    primary_text: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    cta_text: Mapped[str | None] = mapped_column(String(64))
    cta_url: Mapped[str | None] = mapped_column(Text)
    landing_url: Mapped[str | None] = mapped_column(Text)

    variant_count: Mapped[int | None] = mapped_column(Integer)
    reach_band: Mapped[str | None] = mapped_column(String(64))
    impressions_band: Mapped[str | None] = mapped_column(String(64))
    spend_band: Mapped[str | None] = mapped_column(String(64))

    winner_score: Mapped[int | None] = mapped_column(Integer, index=True)
    rising_star_score: Mapped[int | None] = mapped_column(Integer, index=True)

    competitor_id: Mapped[int | None] = mapped_column(
        ForeignKey("competitors.id", ondelete="SET NULL"), index=True
    )

    # Platform-native viewing URL (FB Ad Library / TikTok Ad Library / etc.)
    source_url: Mapped[str | None] = mapped_column(Text)
    # Resolved destination chain — array of hops, last is the final landing page.
    link_chain: Mapped[Any | None] = mapped_column(JSONB)
    final_url: Mapped[str | None] = mapped_column(Text)
    final_domain: Mapped[str | None] = mapped_column(String(255), index=True)
    affiliate_network: Mapped[str | None] = mapped_column(String(64), index=True)
    link_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    hook_type: Mapped[str | None] = mapped_column(String(32), index=True)
    awareness_stage: Mapped[int | None] = mapped_column(Integer)
    copy_framework: Mapped[str | None] = mapped_column(String(32))

    ai_hook: Mapped[str | None] = mapped_column(Text)
    ai_angle: Mapped[str | None] = mapped_column(Text)
    ai_offer: Mapped[str | None] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_rewritten_copy: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    copy_embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    image_embedding: Mapped[list[float] | None] = mapped_column(Vector(768))

    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
