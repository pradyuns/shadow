"""Tests for notification service."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.notification_service import get_user_settings, upsert_setting


class TestGetUserSettings:
    @pytest.mark.asyncio
    async def test_returns_settings(self):
        db = AsyncMock()
        mock_settings = [MagicMock(), MagicMock()]
        result = MagicMock()
        result.scalars.return_value.all.return_value = mock_settings
        db.execute.return_value = result

        settings = await get_user_settings(db, uuid.uuid4())
        assert len(settings) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        settings = await get_user_settings(db, uuid.uuid4())
        assert settings == []


class TestUpsertSetting:
    @pytest.mark.asyncio
    async def test_create_new_setting(self):
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        await upsert_setting(db, uuid.uuid4(), "slack", {"is_enabled": True})
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_setting(self):
        db = AsyncMock()
        existing = MagicMock()
        existing.is_enabled = False
        result = MagicMock()
        result.scalar_one_or_none.return_value = existing
        db.execute.return_value = result

        await upsert_setting(db, uuid.uuid4(), "slack", {"is_enabled": True})
        assert existing.is_enabled is True
        db.commit.assert_called_once()
