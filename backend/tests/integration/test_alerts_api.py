"""Integration tests for alerts API endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.main import app
from app.models.alert import Alert
from app.models.user import User


def _mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.is_active = True
    user.is_admin = False
    user.max_monitors = 50
    return user


def _mock_alert(user_id, **overrides):
    a = MagicMock(spec=Alert)
    defaults = {
        "id": uuid.uuid4(),
        "monitor_id": uuid.uuid4(),
        "user_id": user_id,
        "severity": "high",
        "summary": "Pricing change detected",
        "categories": ["pricing_change"],
        "diff_id": "507f1f77bcf86cd799439011",
        "analysis_id": "507f1f77bcf86cd799439012",
        "is_acknowledged": False,
        "cluster_id": None,
        "acknowledged_at": None,
        "notified_via_slack": False,
        "notified_via_email": False,
        "notified_at": None,
        "notification_error": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(a, k, v)
    return a


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def setup_auth():
    mock_db = AsyncMock()
    user = _mock_user()

    async def _override_user():
        return user

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db

    return user, mock_db


class TestListAlerts:
    """Test GET /api/v1/alerts."""

    @pytest.mark.asyncio
    async def test_list_success(self, setup_auth):
        user, _ = setup_auth
        alerts = [_mock_alert(user.id) for _ in range(3)]

        with patch("app.api.v1.alerts.list_alerts", return_value=(alerts, 3)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get(
                    "/api/v1/alerts",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_with_severity_filter(self, setup_auth):
        user, _ = setup_auth

        with patch("app.api.v1.alerts.list_alerts", return_value=([], 0)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get(
                    "/api/v1/alerts?severity=critical",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200


class TestGetAlert:
    """Test GET /api/v1/alerts/{id}."""

    @pytest.mark.asyncio
    async def test_get_success(self, setup_auth):
        user, _ = setup_auth
        alert = _mock_alert(user.id)

        with patch("app.api.v1.alerts.get_alert", return_value=alert):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get(
                    f"/api/v1/alerts/{alert.id}",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_not_found(self, setup_auth):
        user, _ = setup_auth

        with patch("app.api.v1.alerts.get_alert", return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get(
                    f"/api/v1/alerts/{uuid.uuid4()}",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 404


class TestAcknowledgeAlert:
    """Test PATCH /api/v1/alerts/{id}/acknowledge."""

    @pytest.mark.asyncio
    async def test_acknowledge_success(self, setup_auth):
        user, _ = setup_auth
        alert = _mock_alert(user.id)
        acked_alert = _mock_alert(user.id, is_acknowledged=True, acknowledged_at=datetime.now(timezone.utc))

        with (
            patch("app.api.v1.alerts.get_alert", return_value=alert),
            patch("app.api.v1.alerts.acknowledge_alert", return_value=acked_alert),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.patch(
                    f"/api/v1/alerts/{alert.id}/acknowledge",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_acknowledge_not_found(self, setup_auth):
        user, _ = setup_auth

        with patch("app.api.v1.alerts.get_alert", return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.patch(
                    f"/api/v1/alerts/{uuid.uuid4()}/acknowledge",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 404
