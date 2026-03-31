"""Tests for email verification token and dependency."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.utils.security import create_email_verification_token, decode_token


class TestEmailVerificationToken:
    """Test email verification JWT creation."""

    def test_create_token(self):
        token = create_email_verification_token({"sub": "user-123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_type_is_email_verify(self):
        token = create_email_verification_token({"sub": "user-123"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "email_verify"

    def test_token_preserves_subject(self):
        user_id = str(uuid.uuid4())
        token = create_email_verification_token({"sub": user_id})
        payload = decode_token(token)
        assert payload["sub"] == user_id

    def test_token_has_expiry(self):
        token = create_email_verification_token({"sub": "user-123"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_token_differs_from_access_token(self):
        from app.utils.security import create_access_token

        data = {"sub": "user-123"}
        verify_token = create_email_verification_token(data)
        access_token = create_access_token(data)
        assert verify_token != access_token


class TestRequireVerifiedUser:
    """Test the require_verified_user dependency via API endpoints."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        yield
        app.dependency_overrides.clear()

    def _make_mock_user(self, verified: bool = True):
        mock = MagicMock()
        mock.id = uuid.uuid4()
        mock.email = "test@example.com"
        mock.full_name = "Test User"
        mock.is_active = True
        mock.is_admin = False
        mock.is_email_verified = verified
        mock.email_verified_at = datetime.now(timezone.utc) if verified else None
        mock.max_monitors = 50
        mock.created_at = datetime.now(timezone.utc)
        return mock

    @pytest.mark.asyncio
    async def test_verified_user_can_create_monitor(self):
        from app.api.deps import require_verified_user

        user = self._make_mock_user(verified=True)
        app.dependency_overrides[require_verified_user] = lambda: user

        mock_monitor = MagicMock()
        mock_monitor.id = uuid.uuid4()
        mock_monitor.user_id = user.id
        mock_monitor.name = "Test"
        mock_monitor.url = "https://example.com"
        mock_monitor.competitor_name = None
        mock_monitor.page_type = "homepage"
        mock_monitor.check_interval_hours = 6
        mock_monitor.css_selector = None
        mock_monitor.render_js = False
        mock_monitor.use_firecrawl = False
        mock_monitor.is_active = True
        mock_monitor.next_check_at = datetime.now(timezone.utc)
        mock_monitor.last_checked_at = None
        mock_monitor.last_scrape_status = "pending"
        mock_monitor.last_scrape_error = None
        mock_monitor.last_snapshot_id = None
        mock_monitor.last_change_at = None
        mock_monitor.consecutive_failures = 0
        mock_monitor.noise_patterns = []
        mock_monitor.created_at = datetime.now(timezone.utc)
        mock_monitor.updated_at = datetime.now(timezone.utc)

        mock_db = AsyncMock()

        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        with patch("app.api.v1.monitors.create_monitor", return_value=mock_monitor):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/monitors",
                    json={"name": "Test", "url": "https://example.com", "page_type": "homepage"},
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_unverified_user_blocked_from_creating_monitor(self):
        from app.api.deps import get_current_user

        user = self._make_mock_user(verified=False)
        app.dependency_overrides[get_current_user] = lambda: user

        mock_db = AsyncMock()

        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/monitors",
                json={"name": "Test", "url": "https://example.com", "page_type": "homepage"},
                headers={"Authorization": "Bearer fake-token"},
            )

        assert response.status_code == 403
        assert "Email verification required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_unverified_user_can_read_monitors(self):
        from app.api.deps import get_current_user

        user = self._make_mock_user(verified=False)
        app.dependency_overrides[get_current_user] = lambda: user

        mock_db = AsyncMock()

        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        with patch("app.api.v1.monitors.list_monitors", return_value=([], 0)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get(
                    "/api/v1/monitors",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200


class TestVerifyEmailEndpoint:
    """Test GET /api/v1/auth/verify-email."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        yield
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_verify_email_with_valid_token(self):
        user_id = uuid.uuid4()
        token = create_email_verification_token({"sub": str(user_id)})

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_email_verified = False
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as ac:
            response = await ac.get(f"/api/v1/auth/verify-email?token={token}")

        assert response.status_code == 307
        assert "verified=true" in response.headers["location"]
        assert mock_user.is_email_verified is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_email_with_invalid_token(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as ac:
            response = await ac.get("/api/v1/auth/verify-email?token=invalid-token")

        assert response.status_code == 307
        assert "verify_error=invalid" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_verify_email_with_access_token_rejected(self):
        from app.utils.security import create_access_token

        token = create_access_token({"sub": str(uuid.uuid4())})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as ac:
            response = await ac.get(f"/api/v1/auth/verify-email?token={token}")

        assert response.status_code == 307
        assert "verify_error=invalid" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_verify_already_verified_user(self):
        user_id = uuid.uuid4()
        token = create_email_verification_token({"sub": str(user_id)})

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_email_verified = True
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as ac:
            response = await ac.get(f"/api/v1/auth/verify-email?token={token}")

        assert response.status_code == 307
        assert "verified=true" in response.headers["location"]
        # Should not call commit for already-verified users
        mock_db.commit.assert_not_awaited()


class TestResendVerificationEndpoint:
    """Test POST /api/v1/auth/resend-verification."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        yield
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_resend_for_unverified_user(self):
        from app.api.deps import get_current_user

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "test@example.com"
        mock_user.is_email_verified = False
        mock_user.is_active = True

        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("workers.tasks.email_verification.send_verification_email") as mock_task:
            mock_task.delay = MagicMock()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/auth/resend-verification",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 202
        mock_task.delay.assert_called_once_with(str(mock_user.id))

    @pytest.mark.asyncio
    async def test_resend_for_verified_user_rejected(self):
        from app.api.deps import get_current_user

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "test@example.com"
        mock_user.is_email_verified = True
        mock_user.is_active = True

        app.dependency_overrides[get_current_user] = lambda: mock_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/resend-verification",
                headers={"Authorization": "Bearer fake-token"},
            )

        assert response.status_code == 400
        assert "already verified" in response.json()["detail"]
