"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("max_monitors", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_is_active", "users", ["is_active"])

    # Monitors
    op.create_table(
        "monitors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("competitor_name", sa.String(255), nullable=True),
        sa.Column("page_type", sa.String(50), nullable=False),
        sa.Column("render_js", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("check_interval_hours", sa.Integer(), nullable=False, server_default=sa.text("6")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("next_check_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_scrape_status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("last_scrape_error", sa.Text(), nullable=True),
        sa.Column("last_snapshot_id", sa.String(24), nullable=True),
        sa.Column("last_change_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("noise_patterns", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("css_selector", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "url", name="uq_monitors_user_url"),
    )
    op.create_index("idx_monitors_user_id", "monitors", ["user_id"])
    op.create_index("idx_monitors_is_active", "monitors", ["is_active"])
    op.create_index("idx_monitors_url", "monitors", ["url"])
    op.create_index("idx_monitors_last_scrape_status", "monitors", ["last_scrape_status"])
    op.create_index(
        "idx_monitors_next_check",
        "monitors",
        ["is_active", "next_check_at"],
    )

    # Alerts
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "monitor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("monitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("categories", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("diff_id", sa.String(24), nullable=False),
        sa.Column("analysis_id", sa.String(24), nullable=False),
        sa.Column("is_acknowledged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notified_via_slack", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notified_via_email", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notification_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_alerts_user_id_created_at", "alerts", ["user_id", sa.text("created_at DESC")])
    op.create_index("idx_alerts_monitor_id", "alerts", ["monitor_id"])
    op.create_index("idx_alerts_severity", "alerts", ["severity"])
    op.create_index("idx_alerts_user_acknowledged", "alerts", ["user_id", "is_acknowledged"])

    # Notification Settings
    op.create_table(
        "notification_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("min_severity", sa.String(20), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("slack_webhook_url", sa.Text(), nullable=True),
        sa.Column("email_address", sa.String(255), nullable=True),
        sa.Column("digest_mode", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("digest_hour_utc", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "channel", name="uq_notification_settings_user_channel"),
    )
    op.create_index("idx_notification_settings_user_id", "notification_settings", ["user_id"])

    # API Keys
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("key_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("idx_api_keys_user_id", "api_keys", ["user_id"])


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("notification_settings")
    op.drop_table("alerts")
    op.drop_table("monitors")
    op.drop_table("users")
