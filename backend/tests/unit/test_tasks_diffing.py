"""Tests for diffing task."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestComputeDiff:
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_skip_existing_diff(self, mock_mongo):
        from workers.tasks.diffing import compute_diff

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        existing = {"_id": ObjectId(), "is_empty_after_filter": False}
        mongo_db.diffs.find_one.return_value = existing

        # compute_diff is a bound task, call via the underlying __wrapped__ or directly
        result = compute_diff("mon-1", "snap-1")
        assert result["diff_id"] == str(existing["_id"])
        assert result["has_changes"] is True

    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_snapshot_not_found(self, mock_mongo):
        from workers.tasks.diffing import compute_diff

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        mongo_db.diffs.find_one.return_value = None
        mongo_db.snapshots.find_one.return_value = None

        result = compute_diff("mon-1", str(ObjectId()))
        assert result["has_changes"] is False
        assert result["error"] == "snapshot_not_found"

    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_baseline_snapshot(self, mock_mongo):
        from workers.tasks.diffing import compute_diff

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        snap_id = ObjectId()
        mongo_db.diffs.find_one.return_value = None
        mongo_db.snapshots.find_one.side_effect = [
            {"_id": snap_id, "extracted_text": "hello", "text_hash": "abc"},
            None,  # no previous
        ]

        result = compute_diff("mon-1", str(snap_id))
        assert result["is_baseline"] is True
        assert result["has_changes"] is False
        mongo_db.snapshots.update_one.assert_called_once()

    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_no_change_same_hash(self, mock_mongo):
        from workers.tasks.diffing import compute_diff

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        snap_id = ObjectId()
        prev_id = ObjectId()
        mongo_db.diffs.find_one.return_value = None
        mongo_db.snapshots.find_one.side_effect = [
            {"_id": snap_id, "extracted_text": "hello", "text_hash": "same_hash"},
            {"_id": prev_id, "extracted_text": "hello", "text_hash": "same_hash"},
        ]

        result = compute_diff("mon-1", str(snap_id))
        assert result["has_changes"] is False
        assert result["is_baseline"] is False

    @patch("workers.tasks.analysis.classify_significance")
    @patch("app.db.postgres_sync.get_sync_db")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_meaningful_change_dispatches_classification(self, mock_mongo, mock_pg, mock_classify):
        from workers.tasks.diffing import compute_diff

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db
        db = MagicMock()
        mock_pg.return_value = db

        snap_id = ObjectId()
        prev_id = ObjectId()
        mongo_db.diffs.find_one.return_value = None
        mongo_db.snapshots.find_one.side_effect = [
            {"_id": snap_id, "extracted_text": "New pricing: $129", "text_hash": "hash_new"},
            {"_id": prev_id, "extracted_text": "Old pricing: $99", "text_hash": "hash_old"},
        ]

        monitor = MagicMock()
        monitor.noise_patterns = []
        monitor.name = "Test Monitor"
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        diff_id = ObjectId()
        mongo_db.diffs.insert_one.return_value = MagicMock(inserted_id=diff_id)

        result = compute_diff("mon-1", str(snap_id))
        assert result["has_changes"] is True
        assert result["diff_id"] == str(diff_id)
        mock_classify.delay.assert_called_once_with(str(diff_id))

    @patch("app.db.postgres_sync.get_sync_db")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_noise_only_diff(self, mock_mongo, mock_pg):
        from workers.tasks.diffing import compute_diff

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db
        db = MagicMock()
        mock_pg.return_value = db

        snap_id = ObjectId()
        prev_id = ObjectId()
        mongo_db.diffs.find_one.return_value = None
        mongo_db.snapshots.find_one.side_effect = [
            {"_id": snap_id, "extracted_text": "Page loaded at 2024-01-01T12:00:00Z", "text_hash": "h1"},
            {"_id": prev_id, "extracted_text": "Page loaded at 2024-01-01T11:00:00Z", "text_hash": "h2"},
        ]

        monitor = MagicMock()
        monitor.noise_patterns = []
        monitor.name = "Test"
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        diff_id = ObjectId()
        mongo_db.diffs.insert_one.return_value = MagicMock(inserted_id=diff_id)

        result = compute_diff("mon-1", str(snap_id))
        assert "diff_id" in result
