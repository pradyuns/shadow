"""Integration tests for monitors API endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.main import app
from app.models.monitor import Monitor
from app.models.user import User


def _mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.is_active = True
    user.is_admin = False
    user.max_monitors = 50
    return user


def _mock_monitor(user_id):
    m = MagicMock(spec=Monitor)
    m.id = uuid.uuid4()
    m.user_id = user_id
    m.url = "https://example.com/pricing"
    m.name = "Example Pricing"
    m.competitor_name = "Example Corp"
    m.page_type = "pricing"
    m.render_js = False
    m.use_firecrawl = False
    m.check_interval_hours = 6
    m.is_active = True
    m.next_check_at = datetime.now(timezone.utc)
    m.last_checked_at = None
    m.last_scrape_status = "pending"
    m.last_scrape_error = None
    m.last_snapshot_id = None
    m.last_change_at = None
    m.consecutive_failures = 0
    m.noise_patterns = []
    m.css_selector = None
    m.deleted_at = None
    m.created_at = datetime.now(timezone.utc)
    m.updated_at = datetime.now(timezone.utc)
    return m


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def setup_auth():
    """Set up authenticated client with dependency overrides."""
    mock_db = AsyncMock()
    user = _mock_user()

    async def _override_user():
        return user

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db

    return user, mock_db


class TestCreateMonitor:
    """Test POST /api/v1/monitors."""

    @pytest.mark.asyncio
    async def test_create_success(self, setup_auth):
        user, mock_db = setup_auth
        monitor = _mock_monitor(user.id)

        with patch("app.api.v1.monitors.create_monitor", return_value=monitor):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/monitors",
                    json={
                        "url": "https://example.com/pricing",
                        "name": "Example Pricing",
                        "page_type": "pricing",
                    },
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 201
        assert response.json()["name"] == "Example Pricing"

    @pytest.mark.asyncio
    async def test_create_validation_error(self, setup_auth):
        user, mock_db = setup_auth

        with patch("app.api.v1.monitors.create_monitor", side_effect=ValueError("Monitor limit reached")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/monitors",
                    json={
                        "url": "https://example.com",
                        "name": "Test",
                        "page_type": "pricing",
                    },
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_requires_auth(self):
        """Unauthenticated request should be rejected."""
        app.dependency_overrides.clear()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/monitors",
                json={
                    "url": "https://example.com",
                    "name": "Test",
                    "page_type": "pricing",
                },
            )
        assert response.status_code in (401, 403)


class TestListMonitors:
    """Test GET /api/v1/monitors."""

    @pytest.mark.asyncio
    async def test_list_success(self, setup_auth):
        user, mock_db = setup_auth
        monitors = [_mock_monitor(user.id) for _ in range(3)]

        with patch("app.api.v1.monitors.list_monitors", return_value=(monitors, 3)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get(
                    "/api/v1/monitors",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_empty(self, setup_auth):
        user, mock_db = setup_auth

        with patch("app.api.v1.monitors.list_monitors", return_value=([], 0)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get(
                    "/api/v1/monitors",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestGetMonitor:
    """Test GET /api/v1/monitors/{id}."""

    @pytest.mark.asyncio
    async def test_get_success(self, setup_auth):
        user, mock_db = setup_auth
        monitor = _mock_monitor(user.id)

        with patch("app.api.v1.monitors.get_monitor", return_value=monitor):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get(
                    f"/api/v1/monitors/{monitor.id}",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_not_found(self, setup_auth):
        user, mock_db = setup_auth

        with patch("app.api.v1.monitors.get_monitor", return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get(
                    f"/api/v1/monitors/{uuid.uuid4()}",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 404


class TestDeleteMonitor:
    """Test DELETE /api/v1/monitors/{id}."""

    @pytest.mark.asyncio
    async def test_delete_success(self, setup_auth):
        user, mock_db = setup_auth
        monitor = _mock_monitor(user.id)

        with (
            patch("app.api.v1.monitors.get_monitor", return_value=monitor),
            patch("app.api.v1.monitors.soft_delete_monitor", return_value=None),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.delete(
                    f"/api/v1/monitors/{monitor.id}",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 204


class TestTriggerScrape:
    """Test POST /api/v1/monitors/{id}/scrape."""

    @pytest.mark.asyncio
    async def test_trigger_scrape_accepted(self, setup_auth):
        user, mock_db = setup_auth
        monitor = _mock_monitor(user.id)

        mock_task = MagicMock()
        mock_task.id = "task-123"

        with (
            patch("app.api.v1.monitors.get_monitor", return_value=monitor),
            patch("workers.tasks.scraping.scrape_single_url") as mock_scrape,
        ):
            mock_scrape.delay.return_value = mock_task
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    f"/api/v1/monitors/{monitor.id}/scrape",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 202
        assert response.json()["status"] == "accepted"
        mock_scrape.delay.assert_called_once_with(str(monitor.id), force=True)
