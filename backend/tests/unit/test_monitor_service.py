"""Tests for monitor service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.monitor_service import (
    create_monitor,
    get_monitor,
    list_monitors,
    restore_monitor,
    soft_delete_monitor,
    update_monitor,
)


def _mock_user(max_monitors=50):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.max_monitors = max_monitors
    return user


class TestCreateMonitor:
    @pytest.mark.asyncio
    async def test_create_success(self):
        db = AsyncMock()
        db.add = MagicMock()
        user = _mock_user()

        # Monitor count = 0
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        # No duplicate
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = None
        db.execute.side_effect = [count_result, dup_result]

        monitor = await create_monitor(
            db,
            user,
            {
                "url": "https://example.com/pricing",
                "name": "Test Monitor",
                "page_type": "pricing",
            },
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_limit_reached(self):
        db = AsyncMock()
        user = _mock_user(max_monitors=5)

        count_result = MagicMock()
        count_result.scalar.return_value = 5
        db.execute.return_value = count_result

        with pytest.raises(ValueError, match="limit reached"):
            await create_monitor(
                db,
                user,
                {
                    "url": "https://example.com",
                    "name": "Test",
                    "page_type": "pricing",
                },
            )

    @pytest.mark.asyncio
    async def test_create_unsafe_url(self):
        db = AsyncMock()
        user = _mock_user()

        count_result = MagicMock()
        count_result.scalar.return_value = 0
        db.execute.return_value = count_result

        with pytest.raises(ValueError, match="localhost"):
            await create_monitor(
                db,
                user,
                {
                    "url": "http://localhost:8080/admin",
                    "name": "Test",
                    "page_type": "pricing",
                },
            )

    @pytest.mark.asyncio
    async def test_create_duplicate_url(self):
        db = AsyncMock()
        user = _mock_user()

        count_result = MagicMock()
        count_result.scalar.return_value = 0
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = MagicMock()  # existing monitor
        db.execute.side_effect = [count_result, dup_result]

        with pytest.raises(ValueError, match="already monitoring"):
            await create_monitor(
                db,
                user,
                {
                    "url": "https://example.com",
                    "name": "Test",
                    "page_type": "pricing",
                },
            )

    @pytest.mark.asyncio
    async def test_create_invalid_noise_pattern(self):
        db = AsyncMock()
        user = _mock_user()

        count_result = MagicMock()
        count_result.scalar.return_value = 0
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = None
        db.execute.side_effect = [count_result, dup_result]

        with pytest.raises(ValueError, match="Invalid noise pattern"):
            await create_monitor(
                db,
                user,
                {
                    "url": "https://example.com",
                    "name": "Test",
                    "page_type": "pricing",
                    "noise_patterns": ["[invalid"],
                },
            )


class TestGetMonitor:
    @pytest.mark.asyncio
    async def test_get_found(self):
        db = AsyncMock()
        mock_monitor = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_monitor
        db.execute.return_value = result

        monitor = await get_monitor(db, uuid.uuid4(), uuid.uuid4())
        assert monitor is mock_monitor

    @pytest.mark.asyncio
    async def test_get_not_found(self):
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        monitor = await get_monitor(db, uuid.uuid4(), uuid.uuid4())
        assert monitor is None


class TestListMonitors:
    @pytest.mark.asyncio
    async def test_list_basic(self):
        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 3

        monitors_result = MagicMock()
        mock_monitors = [MagicMock() for _ in range(3)]
        monitors_result.scalars.return_value.all.return_value = mock_monitors

        db.execute.side_effect = [count_result, monitors_result]

        monitors, total = await list_monitors(db, uuid.uuid4(), page=1, per_page=20)
        assert total == 3
        assert len(monitors) == 3


class TestUpdateMonitor:
    @pytest.mark.asyncio
    async def test_update_fields(self):
        db = AsyncMock()
        monitor = MagicMock()
        monitor.name = "Old Name"

        result = await update_monitor(db, monitor, {"name": "New Name"})
        assert monitor.name == "New Name"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_invalid_noise_pattern(self):
        db = AsyncMock()
        monitor = MagicMock()

        with pytest.raises(ValueError, match="Invalid noise pattern"):
            await update_monitor(db, monitor, {"noise_patterns": ["[invalid"]})


class TestSoftDeleteMonitor:
    @pytest.mark.asyncio
    async def test_soft_delete(self):
        db = AsyncMock()
        monitor = MagicMock()

        await soft_delete_monitor(db, monitor)
        assert monitor.is_active is False
        assert monitor.deleted_at is not None
        db.commit.assert_called_once()


class TestRestoreMonitor:
    @pytest.mark.asyncio
    async def test_restore_found(self):
        db = AsyncMock()
        mock_monitor = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_monitor
        db.execute.return_value = result

        monitor = await restore_monitor(db, uuid.uuid4(), uuid.uuid4())
        assert monitor.is_active is True
        assert monitor.deleted_at is None

    @pytest.mark.asyncio
    async def test_restore_not_found(self):
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        monitor = await restore_monitor(db, uuid.uuid4(), uuid.uuid4())
        assert monitor is None
