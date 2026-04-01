import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_diff_requires_monitor_ownership(auth_client):
    user, _ = auth_client
    monitor_id = uuid.uuid4()
    diff_oid = ObjectId()
    mongo_db = MagicMock()
    mongo_db.diffs.find_one = AsyncMock(
        return_value={
            "_id": diff_oid,
            "monitor_id": str(monitor_id),
            "snapshot_before_id": str(ObjectId()),
            "snapshot_after_id": str(ObjectId()),
            "unified_diff": "@@ -1 +1 @@\n-old\n+new\n",
            "filtered_diff": "@@ -1 +1 @@\n-old\n+new\n",
            "diff_lines_added": 1,
            "diff_lines_removed": 1,
            "diff_size_bytes": 24,
            "is_empty_after_filter": False,
            "noise_lines_removed": 0,
            "learned_noise_lines_removed": 0,
            "learned_noise_pattern_hits": {},
            "created_at": datetime.now(timezone.utc),
        }
    )

    with (
        patch("app.api.v1.diffs.get_mongo_db", return_value=mongo_db),
        patch("app.api.v1.diffs.get_monitor", return_value=None),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(
                f"/api/v1/diffs/{diff_oid}",
                headers={"Authorization": "Bearer fake-token"},
            )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_diff_allows_owner(auth_client):
    user, _ = auth_client
    monitor_id = uuid.uuid4()
    diff_oid = ObjectId()
    mongo_db = MagicMock()
    mongo_db.diffs.find_one = AsyncMock(
        return_value={
            "_id": diff_oid,
            "monitor_id": str(monitor_id),
            "snapshot_before_id": str(ObjectId()),
            "snapshot_after_id": str(ObjectId()),
            "unified_diff": "@@ -1 +1 @@\n-old\n+new\n",
            "filtered_diff": "@@ -1 +1 @@\n-old\n+new\n",
            "diff_lines_added": 1,
            "diff_lines_removed": 1,
            "diff_size_bytes": 24,
            "is_empty_after_filter": False,
            "noise_lines_removed": 0,
            "learned_noise_lines_removed": 0,
            "learned_noise_pattern_hits": {},
            "created_at": datetime.now(timezone.utc),
        }
    )

    with (
        patch("app.api.v1.diffs.get_mongo_db", return_value=mongo_db),
        patch("app.api.v1.diffs.get_monitor", return_value=MagicMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(
                f"/api/v1/diffs/{diff_oid}",
                headers={"Authorization": "Bearer fake-token"},
            )

    assert response.status_code == 200
    assert response.json()["id"] == str(diff_oid)
