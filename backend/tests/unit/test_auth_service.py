"""Tests for auth service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.auth_service import (
    authenticate_user,
    create_tokens,
    refresh_tokens,
    register_user,
)


class TestRegisterUser:
    """Test user registration."""

    @pytest.mark.asyncio
    async def test_register_success(self):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        # No existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        user = await register_user(mock_db, "new@example.com", "password123", "New User")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_email_raises(self):
        mock_db = AsyncMock()
        # Existing user found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # existing user
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already registered"):
            await register_user(mock_db, "existing@example.com", "password123", "Existing User")


class TestAuthenticateUser:
    """Test user authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_valid_user(self):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.password_hash = "$2b$12$LJ3m4ys3Lg0dGqYf6GdMBOtest"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with patch("app.services.auth_service.verify_password", return_value=True):
            user = await authenticate_user(mock_db, "test@example.com", "password123")

        assert user is mock_user

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with patch("app.services.auth_service.verify_password", return_value=False):
            user = await authenticate_user(mock_db, "test@example.com", "wrongpassword")

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        user = await authenticate_user(mock_db, "noone@example.com", "password123")
        assert user is None


class TestCreateTokens:
    """Test token pair creation."""

    def test_creates_token_pair(self):
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()

        tokens = create_tokens(mock_user)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0

    def test_access_and_refresh_are_different(self):
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()

        tokens = create_tokens(mock_user)
        assert tokens["access_token"] != tokens["refresh_token"]


class TestRefreshTokens:
    """Test token refresh flow."""

    @pytest.mark.asyncio
    async def test_refresh_valid_token(self):
        mock_db = AsyncMock()
        user_id = uuid.uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with patch("app.services.auth_service.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": str(user_id), "type": "refresh"}
            tokens = await refresh_tokens(mock_db, "valid-refresh-token")

        assert tokens is not None
        assert "access_token" in tokens

    @pytest.mark.asyncio
    async def test_refresh_invalid_token_returns_none(self):
        mock_db = AsyncMock()
        with patch("app.services.auth_service.decode_token", return_value=None):
            tokens = await refresh_tokens(mock_db, "invalid-token")
        assert tokens is None

    @pytest.mark.asyncio
    async def test_refresh_access_token_type_returns_none(self):
        mock_db = AsyncMock()
        with patch("app.services.auth_service.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user-123", "type": "access"}
            tokens = await refresh_tokens(mock_db, "access-token-used-as-refresh")
        assert tokens is None

    @pytest.mark.asyncio
    async def test_refresh_deleted_user_returns_none(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.services.auth_service.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": str(uuid.uuid4()), "type": "refresh"}
            tokens = await refresh_tokens(mock_db, "valid-but-user-deleted")
        assert tokens is None
