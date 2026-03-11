"""Tests for alert suppression logic."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from workers.tasks.suppression import (
    _check_oscillation,
    _check_same_summary,
    _check_severity_escalation,
    _normalize_summary,
    should_suppress_alert,
)


class TestNormalizeSummary:
    def test_removes_numbers(self):
        result = _normalize_summary("Pricing changed from $10 to $15")
        assert "10" not in result
        assert "15" not in result

    def test_removes_percentages(self):
        result = _normalize_summary("Discount increased by 20%")
        assert "20" not in result

    def test_removes_dates(self):
        result = _normalize_summary("Updated on 2024-01-15")
        assert "2024-01-15" not in result

    def test_lowercases(self):
        result = _normalize_summary("PRICING Changed")
        assert result == _normalize_summary("pricing changed")

    def test_collapses_whitespace(self):
        result = _normalize_summary("pricing   changed    a lot")
        assert "  " not in result

    def test_similar_summaries_match(self):
        s1 = _normalize_summary("Pricing changed from $10 to $15")
        s2 = _normalize_summary("Pricing changed from $12 to $18")
        assert s1 == s2


class TestCheckSameSummary:
    def test_suppresses_duplicate_summary(self):
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.all.return_value = [("Pricing changed from $10 to $15",)]
        db.execute.return_value = result_mock

        result = _check_same_summary(db, "monitor-1", "Pricing changed from $12 to $18")
        assert result["suppressed"] is True

    def test_no_suppression_for_new_summary(self):
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.all.return_value = [("Feature added: dark mode",)]
        db.execute.return_value = result_mock

        result = _check_same_summary(db, "monitor-1", "Pricing changed from $12 to $18")
        assert result["suppressed"] is False

    def test_no_suppression_when_no_recent_alerts(self):
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.all.return_value = []
        db.execute.return_value = result_mock

        result = _check_same_summary(db, "monitor-1", "New alert")
        assert result["suppressed"] is False


class TestCheckSeverityEscalation:
    def test_suppresses_same_severity(self):
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.all.return_value = [("medium",)]
        db.execute.return_value = result_mock

        result = _check_severity_escalation(db, "monitor-1", "medium")
        assert result["suppressed"] is True

    def test_suppresses_lower_severity(self):
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.all.return_value = [("critical",)]
        db.execute.return_value = result_mock

        result = _check_severity_escalation(db, "monitor-1", "medium")
        assert result["suppressed"] is True

    def test_allows_higher_severity(self):
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.all.return_value = [("medium",)]
        db.execute.return_value = result_mock

        result = _check_severity_escalation(db, "monitor-1", "critical")
        assert result["suppressed"] is False

    def test_allows_when_no_recent(self):
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.all.return_value = []
        db.execute.return_value = result_mock

        result = _check_severity_escalation(db, "monitor-1", "medium")
        assert result["suppressed"] is False


class TestCheckOscillation:
    def test_suppresses_alternating_pattern(self):
        mongo_db = MagicMock()
        # A, B, A, B, A, B pattern
        hashes = [
            {"text_hash": "hash_a"},
            {"text_hash": "hash_b"},
            {"text_hash": "hash_a"},
            {"text_hash": "hash_b"},
            {"text_hash": "hash_a"},
            {"text_hash": "hash_b"},
        ]
        mongo_db.snapshots.find.return_value = hashes

        result = _check_oscillation(mongo_db, "monitor-1")
        assert result["suppressed"] is True

    def test_no_suppression_with_few_snapshots(self):
        mongo_db = MagicMock()
        hashes = [{"text_hash": "hash_a"}, {"text_hash": "hash_b"}]
        mongo_db.snapshots.find.return_value = hashes

        result = _check_oscillation(mongo_db, "monitor-1")
        assert result["suppressed"] is False

    def test_no_suppression_with_many_unique_hashes(self):
        mongo_db = MagicMock()
        hashes = [
            {"text_hash": "hash_a"},
            {"text_hash": "hash_b"},
            {"text_hash": "hash_c"},
            {"text_hash": "hash_d"},
        ]
        mongo_db.snapshots.find.return_value = hashes

        result = _check_oscillation(mongo_db, "monitor-1")
        assert result["suppressed"] is False

    def test_no_suppression_stable_content(self):
        mongo_db = MagicMock()
        hashes = [
            {"text_hash": "hash_a"},
            {"text_hash": "hash_a"},
            {"text_hash": "hash_a"},
            {"text_hash": "hash_a"},
        ]
        mongo_db.snapshots.find.return_value = hashes

        result = _check_oscillation(mongo_db, "monitor-1")
        assert result["suppressed"] is False


class TestShouldSuppressAlert:
    def test_no_suppression_when_all_rules_pass(self):
        db = MagicMock()
        mongo_db = MagicMock()

        # No recent alerts
        result_mock = MagicMock()
        result_mock.all.return_value = []
        db.execute.return_value = result_mock

        # Few snapshots
        mongo_db.snapshots.find.return_value = []

        result = should_suppress_alert(db, mongo_db, "monitor-1", "New change", "critical")
        assert result["suppressed"] is False

    def test_suppresses_on_first_matching_rule(self):
        db = MagicMock()
        mongo_db = MagicMock()

        # Same summary exists
        result_mock = MagicMock()
        result_mock.all.return_value = [("New change",)]
        db.execute.return_value = result_mock

        result = should_suppress_alert(db, mongo_db, "monitor-1", "New change", "medium")
        assert result["suppressed"] is True
        assert "Similar" in result["reason"]
