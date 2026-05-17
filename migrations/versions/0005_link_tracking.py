"""link tracking — source_url, link_chain, final_url, final_domain, affiliate_network

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ads", sa.Column("source_url", sa.Text()))
    op.add_column("ads", sa.Column("link_chain", postgresql.JSONB()))
    op.add_column("ads", sa.Column("final_url", sa.Text()))
    op.add_column("ads", sa.Column("final_domain", sa.String(length=255)))
    op.add_column("ads", sa.Column("affiliate_network", sa.String(length=64)))
    op.add_column("ads", sa.Column("link_resolved_at", sa.DateTime(timezone=True)))
    op.create_index("ix_ads_final_domain", "ads", ["final_domain"])
    op.create_index("ix_ads_affiliate_network", "ads", ["affiliate_network"])


def downgrade() -> None:
    op.drop_index("ix_ads_affiliate_network", table_name="ads")
    op.drop_index("ix_ads_final_domain", table_name="ads")
    op.drop_column("ads", "link_resolved_at")
    op.drop_column("ads", "affiliate_network")
    op.drop_column("ads", "final_domain")
    op.drop_column("ads", "final_url")
    op.drop_column("ads", "link_chain")
    op.drop_column("ads", "source_url")
