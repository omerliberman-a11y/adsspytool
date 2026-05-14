"""zero-cost re-architecture

Drop apify_runs (replaced by scrape_runs), add normalization_failures,
ai_calls, ad_history, plus new ad fields (media_phash, hook_type,
awareness_stage, copy_framework, rising_star_score, copy/image embeddings).

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Drop the old apify_runs table and create scrape_runs in its place.
    op.drop_index("ix_apify_runs_run_id", table_name="apify_runs")
    op.drop_table("apify_runs")

    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("query_json", postgresql.JSONB()),
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
    op.create_index("ix_scrape_runs_started", "scrape_runs", ["started_at"])

    # 2) normalization_failures
    op.create_table(
        "normalization_failures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("raw_json", postgresql.JSONB()),
        sa.Column("classic_error", sa.Text()),
        sa.Column("llm_output", sa.Text()),
        sa.Column("recovered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3) ai_calls
    op.create_table(
        "ai_calls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("modality", sa.String(length=16), nullable=False),
        sa.Column("purpose", sa.String(length=64)),
        sa.Column("prompt_chars", sa.Integer()),
        sa.Column("output_chars", sa.Integer()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("error", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_calls_created", "ai_calls", ["created_at"])

    # 4) ad_history
    op.create_table(
        "ad_history",
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("ad_id", sa.String(length=128), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16)),
        sa.Column("days_active", sa.Integer()),
        sa.Column("variant_count", sa.Integer()),
        sa.Column("winner_score", sa.Integer()),
        sa.PrimaryKeyConstraint("platform", "ad_id", "snapshot_date", name="pk_ad_history"),
    )

    # 5) New columns on ads
    op.add_column("ads", sa.Column("media_phash", postgresql.ARRAY(sa.String(length=32))))
    op.add_column("ads", sa.Column("hook_type", sa.String(length=32)))
    op.add_column("ads", sa.Column("awareness_stage", sa.Integer()))
    op.add_column("ads", sa.Column("copy_framework", sa.String(length=32)))
    op.add_column("ads", sa.Column("rising_star_score", sa.Integer()))
    op.add_column("ads", sa.Column("copy_embedding", Vector(1024)))
    op.add_column("ads", sa.Column("image_embedding", Vector(768)))
    op.create_index("ix_ads_hook_type", "ads", ["hook_type"])
    op.create_index("ix_ads_rising_star_score", "ads", ["rising_star_score"])


def downgrade() -> None:
    op.drop_index("ix_ads_rising_star_score", table_name="ads")
    op.drop_index("ix_ads_hook_type", table_name="ads")
    op.drop_column("ads", "image_embedding")
    op.drop_column("ads", "copy_embedding")
    op.drop_column("ads", "rising_star_score")
    op.drop_column("ads", "copy_framework")
    op.drop_column("ads", "awareness_stage")
    op.drop_column("ads", "hook_type")
    op.drop_column("ads", "media_phash")

    op.drop_table("ad_history")
    op.drop_index("ix_ai_calls_created", table_name="ai_calls")
    op.drop_table("ai_calls")
    op.drop_table("normalization_failures")
    op.drop_index("ix_scrape_runs_started", table_name="scrape_runs")
    op.drop_table("scrape_runs")

    # Recreate apify_runs to its prior shape (best-effort).
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
