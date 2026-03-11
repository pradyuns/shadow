"""Tests for analysis task."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestClassifySignificance:
    @patch("app.db.postgres_sync.get_sync_db")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_skips_existing_analysis(self, mock_mongo, mock_pg):
        from workers.tasks.analysis import classify_significance

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db
        db = MagicMock()
        mock_pg.return_value = db

        existing = {"_id": ObjectId(), "significance_level": "critical", "alert_id": "alert-1"}
        mongo_db.analyses.find_one.return_value = existing

        result = classify_significance("diff-1")
        assert result["significance"] == "critical"

    @patch("app.db.postgres_sync.get_sync_db")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_diff_not_found(self, mock_mongo, mock_pg):
        from workers.tasks.analysis import classify_significance

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db
        db = MagicMock()
        mock_pg.return_value = db

        mongo_db.analyses.find_one.return_value = None
        mongo_db.diffs.find_one.return_value = None

        result = classify_significance(str(ObjectId()))
        assert result["error"] == "diff_not_found"

    @patch("workers.tasks.notifications.send_notifications")
    @patch("workers.tasks.suppression.should_suppress_alert")
    @patch("workers.classifier.claude_client.classify_change")
    @patch("app.db.postgres_sync.get_sync_db")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_creates_alert_for_critical(self, mock_mongo, mock_pg, mock_classify, mock_suppress, mock_notify):
        from workers.tasks.analysis import classify_significance

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db
        db = MagicMock()
        mock_pg.return_value = db

        diff_id = ObjectId()
        monitor_id = str(uuid.uuid4())

        mongo_db.analyses.find_one.return_value = None
        mongo_db.diffs.find_one.return_value = {
            "_id": diff_id,
            "monitor_id": monitor_id,
            "filtered_diff": "+New pricing: $129\n-Old pricing: $99",
            "snapshot_after_id": str(ObjectId()),
        }

        monitor = MagicMock()
        monitor.competitor_name = "Acme"
        monitor.page_type = "pricing"
        monitor.url = "https://acme.com/pricing"
        monitor.user_id = uuid.uuid4()
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        mock_classify.return_value = {
            "classification": {
                "significance_level": "critical",
                "summary": "Major pricing change",
                "categories": ["pricing"],
            },
            "claude_model": "claude-sonnet-4-20250514",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_cost_usd": 0.001,
            "needs_review": False,
        }

        analysis_oid = ObjectId()
        mongo_db.analyses.insert_one.return_value = MagicMock(inserted_id=analysis_oid)
        mock_suppress.return_value = {"suppressed": False}

        result = classify_significance(str(diff_id))
        assert result["significance"] == "critical"
        assert result["alert_id"] is not None
        db.add.assert_called_once()
        mock_notify.delay.assert_called_once()

    @patch("workers.classifier.claude_client.classify_change")
    @patch("app.db.postgres_sync.get_sync_db")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_skips_alert_for_low_severity(self, mock_mongo, mock_pg, mock_classify):
        from workers.tasks.analysis import classify_significance

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db
        db = MagicMock()
        mock_pg.return_value = db

        diff_id = ObjectId()
        monitor_id = str(uuid.uuid4())

        mongo_db.analyses.find_one.return_value = None
        mongo_db.diffs.find_one.return_value = {
            "_id": diff_id,
            "monitor_id": monitor_id,
            "filtered_diff": "+Minor text update",
            "snapshot_after_id": str(ObjectId()),
        }

        monitor = MagicMock()
        monitor.competitor_name = "Acme"
        monitor.page_type = "pricing"
        monitor.url = "https://acme.com"
        monitor.user_id = uuid.uuid4()
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        mock_classify.return_value = {
            "classification": {
                "significance_level": "low",
                "summary": "Minor text change",
                "categories": ["other"],
            },
            "claude_model": "claude-sonnet-4-20250514",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_cost_usd": 0.001,
            "needs_review": False,
        }

        analysis_oid = ObjectId()
        mongo_db.analyses.insert_one.return_value = MagicMock(inserted_id=analysis_oid)

        result = classify_significance(str(diff_id))
        assert result["significance"] == "low"
        assert result["alert_id"] is None
        db.add.assert_not_called()

    @patch("workers.tasks.suppression.should_suppress_alert")
    @patch("workers.classifier.claude_client.classify_change")
    @patch("app.db.postgres_sync.get_sync_db")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    def test_suppresses_alert(self, mock_mongo, mock_pg, mock_classify, mock_suppress):
        from workers.tasks.analysis import classify_significance

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db
        db = MagicMock()
        mock_pg.return_value = db

        diff_id = ObjectId()
        monitor_id = str(uuid.uuid4())

        mongo_db.analyses.find_one.return_value = None
        mongo_db.diffs.find_one.return_value = {
            "_id": diff_id,
            "monitor_id": monitor_id,
            "filtered_diff": "+Change",
            "snapshot_after_id": str(ObjectId()),
        }

        monitor = MagicMock()
        monitor.competitor_name = "Acme"
        monitor.page_type = "pricing"
        monitor.url = "https://acme.com"
        monitor.user_id = uuid.uuid4()
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        mock_classify.return_value = {
            "classification": {
                "significance_level": "medium",
                "summary": "Pricing update",
                "categories": ["pricing"],
            },
            "claude_model": "claude-sonnet-4-20250514",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_cost_usd": 0.001,
            "needs_review": False,
        }

        analysis_oid = ObjectId()
        mongo_db.analyses.insert_one.return_value = MagicMock(inserted_id=analysis_oid)
        mock_suppress.return_value = {"suppressed": True, "reason": "Similar alert sent"}

        result = classify_significance(str(diff_id))
        assert result["suppressed"] is True
        assert result["alert_id"] is None
        db.add.assert_not_called()
