"""Add alert clusters table and cluster_id to alerts

Revision ID: 004
Revises: 003
Create Date: 2026-03-24
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("competitor_name", sa.String(255), nullable=False, index=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("alert_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("categories", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("summary_keywords", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.add_column(
        "alerts",
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alert_clusters.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_alerts_cluster_id", "alerts", ["cluster_id"])


def downgrade() -> None:
    op.drop_index("ix_alerts_cluster_id", "alerts")
    op.drop_column("alerts", "cluster_id")
    op.drop_table("alert_clusters")
