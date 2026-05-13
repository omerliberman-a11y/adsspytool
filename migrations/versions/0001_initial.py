"""initial: ads + apify_runs + pgvector

Revision ID: 0001
Revises:
Create Date: 2026-05-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "ads",
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("ad_id", sa.String(length=128), nullable=False),
        sa.Column("advertiser_name", sa.Text()),
        sa.Column("advertiser_page_id", sa.String(length=128)),
        sa.Column("advertiser_url", sa.Text()),
        sa.Column("first_seen", sa.DateTime(timezone=True)),
        sa.Column("last_seen", sa.DateTime(timezone=True)),
        sa.Column("days_active", sa.Integer()),
        sa.Column("countries", postgresql.ARRAY(sa.String())),
        sa.Column("languages", postgresql.ARRAY(sa.String())),
        sa.Column("placements", postgresql.ARRAY(sa.String())),
        sa.Column("creative_type", sa.String(length=16)),
        sa.Column("media_urls", postgresql.ARRAY(sa.Text())),
        sa.Column("local_media_paths", postgresql.ARRAY(sa.Text())),
        sa.Column("headline", sa.Text()),
        sa.Column("primary_text", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("cta_text", sa.String(length=64)),
        sa.Column("cta_url", sa.Text()),
        sa.Column("landing_url", sa.Text()),
        sa.Column("variant_count", sa.Integer()),
        sa.Column("reach_band", sa.String(length=64)),
        sa.Column("impressions_band", sa.String(length=64)),
        sa.Column("spend_band", sa.String(length=64)),
        sa.Column("winner_score", sa.Integer()),
        sa.Column("ai_hook", sa.Text()),
        sa.Column("ai_angle", sa.Text()),
        sa.Column("ai_offer", sa.Text()),
        sa.Column("ai_framework", sa.String(length=64)),
        sa.Column("ai_summary", sa.Text()),
        sa.Column("ai_rewritten_copy", postgresql.ARRAY(sa.Text())),
        sa.Column("raw_json", postgresql.JSONB()),
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
        sa.PrimaryKeyConstraint("platform", "ad_id", name="pk_ads"),
    )
    op.create_index("ix_ads_winner_score", "ads", ["winner_score"])
    op.create_index("ix_ads_platform_first_seen", "ads", ["platform", "first_seen"])

    op.create_table(
        "apify_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=128)),
        sa.Column("dataset_id", sa.String(length=128)),
        sa.Column("input_json", postgresql.JSONB()),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("cost_usd", sa.Float()),
        sa.Column("duration_secs", sa.Float()),
        sa.Column("item_count", sa.Integer()),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_apify_runs_run_id", "apify_runs", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_apify_runs_run_id", table_name="apify_runs")
    op.drop_table("apify_runs")
    op.drop_index("ix_ads_platform_first_seen", table_name="ads")
    op.drop_index("ix_ads_winner_score", table_name="ads")
    op.drop_table("ads")
