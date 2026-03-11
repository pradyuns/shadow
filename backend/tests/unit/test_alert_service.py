"""Tests for alert service."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.alert_service import acknowledge_alert, get_alert, list_alerts


class TestListAlerts:
    @pytest.mark.asyncio
    async def test_list_basic(self):
        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 5

        alerts_result = MagicMock()
        mock_alerts = [MagicMock() for _ in range(5)]
        alerts_result.scalars.return_value.all.return_value = mock_alerts

        db.execute.side_effect = [count_result, alerts_result]

        alerts, total = await list_alerts(db, uuid.uuid4(), page=1, per_page=20)
        assert total == 5
        assert len(alerts) == 5

    @pytest.mark.asyncio
    async def test_list_with_filters(self):
        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 2

        alerts_result = MagicMock()
        alerts_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]

        db.execute.side_effect = [count_result, alerts_result]

        alerts, total = await list_alerts(
            db,
            uuid.uuid4(),
            page=1,
            per_page=20,
            severity="critical",
            is_acknowledged=False,
        )
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_empty(self):
        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        alerts_result = MagicMock()
        alerts_result.scalars.return_value.all.return_value = []

        db.execute.side_effect = [count_result, alerts_result]

        alerts, total = await list_alerts(db, uuid.uuid4(), page=1, per_page=20)
        assert total == 0
        assert alerts == []


class TestGetAlert:
    @pytest.mark.asyncio
    async def test_get_found(self):
        db = AsyncMock()
        mock_alert = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_alert
        db.execute.return_value = result

        alert = await get_alert(db, uuid.uuid4(), uuid.uuid4())
        assert alert is mock_alert

    @pytest.mark.asyncio
    async def test_get_not_found(self):
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        alert = await get_alert(db, uuid.uuid4(), uuid.uuid4())
        assert alert is None


class TestAcknowledgeAlert:
    @pytest.mark.asyncio
    async def test_acknowledge(self):
        db = AsyncMock()
        alert = MagicMock()
        alert.is_acknowledged = False

        result = await acknowledge_alert(db, alert)
        assert alert.is_acknowledged is True
        assert alert.acknowledged_at is not None
        db.commit.assert_called_once()
