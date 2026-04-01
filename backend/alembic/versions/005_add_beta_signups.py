"""Add beta signups table

Revision ID: 005
Revises: 004
Create Date: 2026-03-31
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "beta_signups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("email_normalized", sa.String(255), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="landing_page"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_beta_signups_email_normalized", "beta_signups", ["email_normalized"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_beta_signups_email_normalized", table_name="beta_signups")
    op.drop_table("beta_signups")
