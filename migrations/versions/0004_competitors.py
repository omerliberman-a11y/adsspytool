"""competitors table + ads.competitor_id FK

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "competitors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255)),
        sa.Column("notes", sa.Text()),
        sa.Column("tags", postgresql.ARRAY(sa.String())),
        sa.Column("fb_page_url", sa.Text()),
        sa.Column("fb_page_id", sa.String(length=64)),
        sa.Column("instagram_handle", sa.String(length=64)),
        sa.Column("tiktok_handle", sa.String(length=64)),
        sa.Column("twitter_handle", sa.String(length=64)),
        sa.Column("youtube_channel", sa.String(length=255)),
        sa.Column("linkedin_company", sa.String(length=255)),
        sa.Column("tech_stack", postgresql.ARRAY(sa.String())),
        sa.Column("pixels", postgresql.ARRAY(sa.String())),
        sa.Column("domain_created_at", sa.Date()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("scan_interval_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("last_enriched_at", sa.DateTime(timezone=True)),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True)),
        sa.Column("last_scan_error", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain", name="uq_competitors_domain"),
    )
    op.create_index("ix_competitors_domain", "competitors", ["domain"])
    op.create_index("ix_competitors_fb_page_id", "competitors", ["fb_page_id"])

    op.add_column("ads", sa.Column("competitor_id", sa.Integer()))
    op.create_foreign_key(
        "fk_ads_competitor_id",
        "ads",
        "competitors",
        ["competitor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_ads_competitor_id", "ads", ["competitor_id"])


def downgrade() -> None:
    op.drop_index("ix_ads_competitor_id", table_name="ads")
    op.drop_constraint("fk_ads_competitor_id", "ads", type_="foreignkey")
    op.drop_column("ads", "competitor_id")

    op.drop_index("ix_competitors_fb_page_id", table_name="competitors")
    op.drop_index("ix_competitors_domain", table_name="competitors")
    op.drop_table("competitors")
