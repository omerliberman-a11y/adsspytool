"""tasks table for Postgres-backed task queue

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error", sa.Text()),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_kind", "tasks", ["kind"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_scheduled_for", "tasks", ["scheduled_for"])
    op.create_index(
        "ix_tasks_dispatch_lookup",
        "tasks",
        ["status", "priority", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_dispatch_lookup", table_name="tasks")
    op.drop_index("ix_tasks_scheduled_for", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_kind", table_name="tasks")
    op.drop_table("tasks")
