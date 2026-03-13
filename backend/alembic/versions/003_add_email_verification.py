"""Add email verification columns to users

Revision ID: 003
Revises: 002
Create Date: 2026-03-13
"""

import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "is_email_verified")
