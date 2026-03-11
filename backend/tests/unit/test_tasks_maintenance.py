"""Tests for maintenance tasks."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestCleanupOldSnapshots:
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_cleanup_deletes_old_documents(self, mock_mongo):
        from workers.tasks.maintenance import cleanup_old_snapshots

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        mongo_db.snapshots.delete_many.return_value = MagicMock(deleted_count=10)
        mongo_db.diffs.delete_many.return_value = MagicMock(deleted_count=5)
        mongo_db.analyses.delete_many.return_value = MagicMock(deleted_count=3)

        result = cleanup_old_snapshots(days=30)

        assert result["deleted_snapshots"] == 10
        assert result["deleted_diffs"] == 5
        assert result["deleted_analyses"] == 3

    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_cleanup_handles_exception(self, mock_mongo):
        from workers.tasks.maintenance import cleanup_old_snapshots

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db
        mongo_db.snapshots.delete_many.side_effect = Exception("DB error")

        result = cleanup_old_snapshots(days=30)
        assert "error" in result


class TestCleanupDeletedMonitors:
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_no_monitors_to_delete(self, mock_pg, mock_mongo):
        from workers.tasks.maintenance import cleanup_deleted_monitors

        db = MagicMock()
        mock_pg.return_value = db
        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute.return_value = result_mock

        result = cleanup_deleted_monitors()
        assert result["deleted_monitors"] == 0
        assert result["deleted_mongo_docs"] == 0

    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_deletes_expired_monitors(self, mock_pg, mock_mongo):
        from workers.tasks.maintenance import cleanup_deleted_monitors

        db = MagicMock()
        mock_pg.return_value = db
        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        monitor1 = MagicMock()
        monitor1.id = "mon-1"
        monitor2 = MagicMock()
        monitor2.id = "mon-2"

        select_result = MagicMock()
        select_result.scalars.return_value.all.return_value = [monitor1, monitor2]
        db.execute.side_effect = [select_result, MagicMock(), MagicMock()]

        mongo_db.snapshots.delete_many.return_value = MagicMock(deleted_count=5)
        mongo_db.diffs.delete_many.return_value = MagicMock(deleted_count=3)
        mongo_db.analyses.delete_many.return_value = MagicMock(deleted_count=1)

        result = cleanup_deleted_monitors()
        assert result["deleted_monitors"] == 2
        assert result["deleted_mongo_docs"] == 18  # (5+3+1) * 2

    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_handles_exception(self, mock_pg, mock_mongo):
        from workers.tasks.maintenance import cleanup_deleted_monitors

        db = MagicMock()
        mock_pg.return_value = db
        db.execute.side_effect = Exception("DB error")

        result = cleanup_deleted_monitors()
        assert "error" in result
        db.rollback.assert_called_once()
