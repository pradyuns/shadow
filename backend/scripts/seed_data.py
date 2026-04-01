#!/usr/bin/env python3
"""Seed the database with sample data for development.

Usage:
    python scripts/seed_data.py

Requires DATABASE_URL_SYNC to be set (or .env file).
Creates sample users, monitors, and alerts for local development.
"""

import os
import secrets
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.utils.security import hash_password  # noqa: E402


def _get_seed_password(env_var_name: str) -> tuple[str, bool]:
    password = os.getenv(env_var_name)
    if password:
        return password, True
    return secrets.token_urlsafe(16), False


def seed():
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from app.models.alert import Alert
    from app.models.base import Base
    from app.models.monitor import Monitor
    from app.models.notification_setting import NotificationSetting
    from app.models.user import User

    engine = create_engine(settings.database_url_sync)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        # Check if data already exists
        existing = db.execute(text("SELECT count(*) FROM users")).scalar()
        if existing > 0:
            print(f"Database already has {existing} users. Skipping seed.")
            return

        now = datetime.now(timezone.utc)
        admin_password, admin_password_from_env = _get_seed_password("SEED_ADMIN_PASSWORD")
        demo_password, demo_password_from_env = _get_seed_password("SEED_DEMO_PASSWORD")

        # Create users
        admin = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            password_hash=hash_password(admin_password),
            full_name="Admin User",
            is_active=True,
            is_admin=True,
            max_monitors=100,
        )
        demo_user = User(
            id=uuid.uuid4(),
            email="demo@example.com",
            password_hash=hash_password(demo_password),
            full_name="Demo User",
            is_active=True,
            is_admin=False,
            max_monitors=50,
        )
        db.add_all([admin, demo_user])
        db.flush()

        # Create monitors
        monitors_data = [
            {
                "url": "https://stripe.com/pricing",
                "name": "Stripe Pricing",
                "competitor_name": "Stripe",
                "page_type": "pricing",
                "check_interval_hours": 6,
            },
            {
                "url": "https://www.twilio.com/en-us/pricing",
                "name": "Twilio Pricing",
                "competitor_name": "Twilio",
                "page_type": "pricing",
                "check_interval_hours": 12,
            },
            {
                "url": "https://slack.com/features",
                "name": "Slack Features",
                "competitor_name": "Slack",
                "page_type": "feature",
                "check_interval_hours": 24,
            },
            {
                "url": "https://notion.so/product",
                "name": "Notion Product Page",
                "competitor_name": "Notion",
                "page_type": "product",
                "check_interval_hours": 12,
            },
            {
                "url": "https://linear.app/changelog",
                "name": "Linear Changelog",
                "competitor_name": "Linear",
                "page_type": "changelog",
                "check_interval_hours": 6,
            },
        ]

        monitors = []
        for mdata in monitors_data:
            monitor = Monitor(
                id=uuid.uuid4(),
                user_id=demo_user.id,
                url=mdata["url"],
                name=mdata["name"],
                competitor_name=mdata["competitor_name"],
                page_type=mdata["page_type"],
                check_interval_hours=mdata["check_interval_hours"],
                is_active=True,
                next_check_at=now,
                last_scrape_status="pending",
                consecutive_failures=0,
                noise_patterns=[],
                render_js=False,
            )
            monitors.append(monitor)
            db.add(monitor)
        db.flush()

        # Create sample alerts
        severities = ["critical", "high", "medium", "low"]
        summaries = [
            "Enterprise pricing increased from $99/mo to $149/mo",
            "New 'Business Plus' tier added to pricing page",
            "Feature comparison table updated with 3 new entries",
            "Minor copy change on product description",
        ]
        for i, (sev, summ) in enumerate(zip(severities, summaries)):
            alert = Alert(
                id=uuid.uuid4(),
                monitor_id=monitors[i % len(monitors)].id,
                user_id=demo_user.id,
                severity=sev,
                summary=summ,
                categories=["pricing_change" if "pricing" in summ.lower() else "feature_update"],
                diff_id=f"seed_diff_{i}",
                analysis_id=f"seed_analysis_{i}",
                is_acknowledged=i > 1,  # First two unacknowledged
                acknowledged_at=now if i > 1 else None,
                created_at=now - timedelta(hours=i * 6),
            )
            db.add(alert)

        # Create notification settings
        slack_setting = NotificationSetting(
            id=uuid.uuid4(),
            user_id=demo_user.id,
            channel="slack",
            is_enabled=True,
            min_severity="medium",
            slack_webhook_url="https://hooks.slack.com/services/EXAMPLE/EXAMPLE/EXAMPLE",
        )
        email_setting = NotificationSetting(
            id=uuid.uuid4(),
            user_id=demo_user.id,
            channel="email",
            is_enabled=True,
            min_severity="high",
            email_address="demo@example.com",
        )
        db.add_all([slack_setting, email_setting])

        db.commit()

        admin_password_display = "<from SEED_ADMIN_PASSWORD>" if admin_password_from_env else admin_password
        demo_password_display = "<from SEED_DEMO_PASSWORD>" if demo_password_from_env else demo_password

        print("Seed data created successfully!")
        print(f"  Users: 2 (admin@example.com / {admin_password_display}, demo@example.com / {demo_password_display})")
        print(f"  Monitors: {len(monitors)}")
        print(f"  Alerts: {len(severities)}")
        print("  Notification settings: 2 (slack, email)")


if __name__ == "__main__":
    seed()
