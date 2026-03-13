"""Integration tests for auth API endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestRegisterEndpoint:
    """Test POST /api/v1/auth/register."""

    @pytest.mark.asyncio
    async def test_register_success(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "new@example.com"
        mock_user.full_name = "New User"
        mock_user.is_active = True
        mock_user.is_admin = False
        mock_user.is_email_verified = False
        mock_user.max_monitors = 50
        mock_user.created_at = datetime.now(timezone.utc)

        with (
            patch("app.api.v1.auth.register_user", return_value=mock_user),
            patch("workers.tasks.email_verification.send_verification_email") as mock_task,
        ):
            mock_task.delay = MagicMock()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "new@example.com",
                        "password": "password123",
                        "full_name": "New User",
                    },
                )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        with patch("app.api.v1.auth.register_user", side_effect=ValueError("Email already registered")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "existing@example.com",
                        "password": "password123",
                        "full_name": "Existing User",
                    },
                )

        assert response.status_code == 409
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/register",
                json={
                    "email": "not-an-email",
                    "password": "password123",
                    "full_name": "Test",
                },
            )

        assert response.status_code == 422
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_register_short_password(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/register",
                json={
                    "email": "test@example.com",
                    "password": "short",
                    "full_name": "Test",
                },
            )

        assert response.status_code == 422
        app.dependency_overrides.clear()


class TestLoginEndpoint:
    """Test POST /api/v1/auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()

        with (
            patch("app.api.v1.auth.authenticate_user", return_value=mock_user),
            patch(
                "app.api.v1.auth.create_tokens",
                return_value={
                    "access_token": "test-access",
                    "refresh_token": "test-refresh",
                    "token_type": "bearer",
                    "expires_in": 1800,
                },
            ),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/auth/login",
                    json={
                        "email": "test@example.com",
                        "password": "password123",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        with patch("app.api.v1.auth.authenticate_user", return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/auth/login",
                    json={
                        "email": "test@example.com",
                        "password": "wrongpassword",
                    },
                )

        assert response.status_code == 401
        app.dependency_overrides.clear()


class TestRefreshEndpoint:
    """Test POST /api/v1/auth/refresh."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        with patch(
            "app.api.v1.auth.refresh_tokens",
            return_value={
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "token_type": "bearer",
                "expires_in": 1800,
            },
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/auth/refresh",
                    json={
                        "refresh_token": "valid-refresh-token",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new-access"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override

        with patch("app.api.v1.auth.refresh_tokens", return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/auth/refresh",
                    json={
                        "refresh_token": "invalid-token",
                    },
                )

        assert response.status_code == 401
        app.dependency_overrides.clear()
