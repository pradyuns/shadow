"""Integration test fixtures.

These tests use FastAPI TestClient with dependency overrides.
External services (DB, Redis, etc.) are mocked.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.main import app
from app.models.user import User


def _make_mock_user(**overrides):
    """Create a mock user object."""
    defaults = {
        "id": uuid.uuid4(),
        "email": "test@example.com",
        "password_hash": "hashed",
        "full_name": "Test User",
        "is_active": True,
        "is_admin": False,
        "max_monitors": 50,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


@pytest.fixture
def mock_user():
    """A standard mock user."""
    return _make_mock_user()


@pytest.fixture
def mock_db():
    """Mock async database session."""
    return AsyncMock()


@pytest.fixture
def auth_client(mock_user, mock_db):
    """Authenticated async test client with dependency overrides."""

    async def _override_get_current_user():
        return mock_user

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_db] = _override_get_db

    yield mock_user, mock_db

    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client(mock_db):
    """Unauthenticated test client (only DB override, no auth)."""

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db

    yield mock_db

    app.dependency_overrides.clear()
