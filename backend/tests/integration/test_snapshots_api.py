import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_snapshot_requires_monitor_ownership(auth_client):
    user, _ = auth_client
    monitor_id = uuid.uuid4()
    snapshot_oid = ObjectId()
    mongo_db = MagicMock()
    mongo_db.snapshots.find_one = AsyncMock(
        return_value={
            "_id": snapshot_oid,
            "monitor_id": str(monitor_id),
            "url": "https://example.com/pricing",
            "http_status": 200,
            "render_method": "httpx",
            "text_hash": "abc123",
            "fetch_duration_ms": 123,
            "status": "extracted",
            "is_baseline": False,
            "created_at": datetime.now(timezone.utc),
            "extracted_text": "hello",
            "raw_html": "<html>hello</html>",
        }
    )

    with (
        patch("app.api.v1.snapshots.get_mongo_db", return_value=mongo_db),
        patch("app.api.v1.snapshots.get_monitor", return_value=None),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(
                f"/api/v1/snapshots/{snapshot_oid}",
                headers={"Authorization": "Bearer fake-token"},
            )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_snapshot_allows_owner(auth_client):
    user, _ = auth_client
    monitor_id = uuid.uuid4()
    snapshot_oid = ObjectId()
    mongo_db = MagicMock()
    mongo_db.snapshots.find_one = AsyncMock(
        return_value={
            "_id": snapshot_oid,
            "monitor_id": str(monitor_id),
            "url": "https://example.com/pricing",
            "http_status": 200,
            "render_method": "httpx",
            "text_hash": "abc123",
            "fetch_duration_ms": 123,
            "status": "extracted",
            "is_baseline": False,
            "created_at": datetime.now(timezone.utc),
            "extracted_text": "hello",
            "raw_html": "<html>hello</html>",
        }
    )

    with (
        patch("app.api.v1.snapshots.get_mongo_db", return_value=mongo_db),
        patch("app.api.v1.snapshots.get_monitor", return_value=MagicMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(
                f"/api/v1/snapshots/{snapshot_oid}",
                headers={"Authorization": "Bearer fake-token"},
            )

    assert response.status_code == 200
    assert response.json()["id"] == str(snapshot_oid)
