"""Root test configuration and shared fixtures."""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Override settings BEFORE any app imports
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("MONGODB_URL", "mongodb://test:test@localhost:27017/test")
os.environ.setdefault("MONGODB_DATABASE", "test_compmon")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("REDIS_RESULT_URL", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_CACHE_URL", "redis://localhost:6379/2")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("SENDGRID_API_KEY", "test-sendgrid-key")
os.environ.setdefault("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test/test/test")

from app.config import settings

# Configure Celery for testing — run tasks eagerly (synchronously)
# and don't try to connect to a real broker
from workers.celery_app import celery_app

celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
    broker_url="memory://",
    result_backend="cache+memory://",
)


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": uuid.uuid4(),
        "email": "test@example.com",
        "password_hash": "$2b$12$LJ3m4ys3Lg0dGqYf6GdMBOtest",
        "full_name": "Test User",
        "is_active": True,
        "is_admin": False,
        "max_monitors": 50,
    }


@pytest.fixture
def sample_monitor_data(sample_user_data):
    """Sample monitor data for testing."""
    return {
        "id": uuid.uuid4(),
        "user_id": sample_user_data["id"],
        "url": "https://example.com/pricing",
        "name": "Example Pricing",
        "competitor_name": "Example Corp",
        "page_type": "pricing",
        "render_js": False,
        "use_firecrawl": False,
        "check_interval_hours": 6,
        "is_active": True,
        "next_check_at": datetime.now(timezone.utc),
        "last_checked_at": None,
        "last_scrape_status": "pending",
        "consecutive_failures": 0,
        "noise_patterns": [],
        "css_selector": None,
    }


@pytest.fixture
def sample_alert_data(sample_user_data, sample_monitor_data):
    """Sample alert data for testing."""
    return {
        "id": uuid.uuid4(),
        "monitor_id": sample_monitor_data["id"],
        "user_id": sample_user_data["id"],
        "severity": "high",
        "summary": "Pricing increased by 20%",
        "categories": ["pricing_change"],
        "diff_id": "507f1f77bcf86cd799439011",
        "analysis_id": "507f1f77bcf86cd799439012",
        "is_acknowledged": False,
        "acknowledged_at": None,
        "notified_via_slack": False,
        "notified_via_email": False,
        "notified_at": None,
        "notification_error": None,
        "created_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def notification_payload():
    """Sample notification payload."""
    from workers.notifier.base import NotificationPayload

    return NotificationPayload(
        alert_id="test-alert-123",
        monitor_name="Example Pricing",
        competitor_name="Example Corp",
        url="https://example.com/pricing",
        page_type="pricing",
        severity="high",
        summary="Pricing page updated: Enterprise plan increased from $99 to $129/month",
        categories=["pricing_change"],
        dashboard_url="https://app.compmon.io",
    )


@pytest.fixture
def sample_html_v1():
    """Simple product page version 1."""
    return """<!DOCTYPE html>
<html>
<head><title>Example Pricing</title></head>
<body>
<script>var tracking = "abc123";</script>
<style>body { font-family: sans-serif; }</style>
<h1>Pricing</h1>
<div class="plans">
  <div class="plan">
    <h2>Starter</h2>
    <p class="price">$29/month</p>
    <ul>
      <li>5 users</li>
      <li>10GB storage</li>
    </ul>
  </div>
  <div class="plan">
    <h2>Enterprise</h2>
    <p class="price">$99/month</p>
    <ul>
      <li>Unlimited users</li>
      <li>100GB storage</li>
    </ul>
  </div>
</div>
<footer>Copyright 2024 Example Corp</footer>
</body>
</html>"""


@pytest.fixture
def sample_html_v2():
    """Same page with pricing changes."""
    return """<!DOCTYPE html>
<html>
<head><title>Example Pricing</title></head>
<body>
<script>var tracking = "def456";</script>
<style>body { font-family: sans-serif; }</style>
<h1>Pricing</h1>
<div class="plans">
  <div class="plan">
    <h2>Starter</h2>
    <p class="price">$29/month</p>
    <ul>
      <li>5 users</li>
      <li>10GB storage</li>
    </ul>
  </div>
  <div class="plan">
    <h2>Enterprise</h2>
    <p class="price">$129/month</p>
    <ul>
      <li>Unlimited users</li>
      <li>200GB storage</li>
      <li>Priority support</li>
    </ul>
  </div>
</div>
<footer>Copyright 2024 Example Corp</footer>
</body>
</html>"""
