"""Integration tests for public API endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestClosedBetaSignup:
    """Test POST /api/v1/public/beta-signups."""

    @pytest.mark.asyncio
    async def test_beta_signup_accepted_for_new_email(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override
        mock_db.add = MagicMock()

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = execute_result

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/public/beta-signups", json={"email": "NewUser@Example.com"})

        assert response.status_code == 202
        assert response.json() == {"status": "accepted"}
        mock_db.add.assert_called_once()
        saved = mock_db.add.call_args[0][0]
        assert saved.email == "NewUser@example.com"
        assert saved.email_normalized == "newuser@example.com"
        mock_db.commit.assert_awaited_once()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_beta_signup_accepted_for_duplicate_email(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override
        mock_db.add = MagicMock()

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = "existing-id"
        mock_db.execute.return_value = execute_result

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/public/beta-signups", json={"email": "existing@example.com"})

        assert response.status_code == 202
        assert response.json() == {"status": "accepted"}
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_awaited()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_beta_signup_rejects_invalid_email(self, mock_db):
        from app.db.postgres import get_db

        async def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override
        mock_db.add = MagicMock()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/public/beta-signups", json={"email": "not-an-email"})

        assert response.status_code == 422
        app.dependency_overrides.clear()
