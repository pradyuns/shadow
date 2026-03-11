"""Add use_firecrawl column to monitors

Revision ID: 002
Revises: 001
Create Date: 2026-03-11
"""

import sqlalchemy as sa

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monitors",
        sa.Column("use_firecrawl", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("monitors", "use_firecrawl")
