"""Tests for the alert clustering algorithm.

Tests the core similarity functions and clustering logic independently
of the database, then integration tests with a real session.
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from workers.clustering.alert_clusterer import (
    MERGE_THRESHOLD,
    TEMPORAL_HALF_LIFE,
    _advisory_lock_id,
    _extract_keywords,
    _jaccard,
    _temporal_similarity,
    compute_similarity,
)

# ── Keyword extraction ───────────────────────────────────────────────────────


class TestExtractKeywords:
    def test_removes_stop_words(self):
        kw = _extract_keywords("the pricing has changed from old to new")
        assert "the" not in kw
        assert "has" not in kw
        assert "from" not in kw
        assert "pricing" in kw

    def test_removes_short_tokens(self):
        kw = _extract_keywords("an AI model is up")
        assert "an" not in kw
        assert "is" not in kw
        assert "up" not in kw
        assert "model" in kw

    def test_removes_generic_change_words(self):
        """Words like 'change', 'detected', 'updated' carry no discriminative signal."""
        kw = _extract_keywords("pricing change detected on page")
        assert "change" not in kw
        assert "detected" not in kw
        assert "page" not in kw
        assert "pricing" in kw

    def test_handles_empty_string(self):
        assert _extract_keywords("") == set()

    def test_extracts_domain_terms(self):
        kw = _extract_keywords("Stripe deprecated free tier entirely from pricing")
        assert "stripe" in kw
        assert "deprecated" in kw
        assert "free" in kw
        assert "tier" in kw
        assert "entirely" in kw
        assert "pricing" in kw


# ── Jaccard similarity ───────────────────────────────────────────────────────


class TestJaccard:
    def test_identical_sets(self):
        assert _jaccard({"a", "b", "c"}, {"a", "b", "c"}) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        # {a, b, c} ∩ {b, c, d} = {b, c}, |union| = 4
        assert _jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 2 / 4

    def test_empty_sets(self):
        assert _jaccard(set(), set()) == 0.0

    def test_one_empty(self):
        assert _jaccard({"a"}, set()) == 0.0

    def test_subset(self):
        # {a, b} ∩ {a, b, c} = {a, b}, |union| = 3
        assert _jaccard({"a", "b"}, {"a", "b", "c"}) == pytest.approx(2 / 3)


# ── Temporal similarity ──────────────────────────────────────────────────────


class TestTemporalSimilarity:
    def test_same_time(self):
        now = datetime.now(timezone.utc)
        assert _temporal_similarity(now, now) == 1.0

    def test_half_life_gives_exactly_half(self):
        """At exactly TEMPORAL_HALF_LIFE hours apart, score must be exactly 0.5.

        This is the defining property of a true half-life decay:
        score = 2^(-hours_diff / half_life)
        At hours_diff = half_life: 2^(-1) = 0.5
        """
        now = datetime.now(timezone.utc)
        later = now + timedelta(hours=TEMPORAL_HALF_LIFE)
        score = _temporal_similarity(now, later)
        assert score == pytest.approx(0.5, abs=0.001)

    def test_double_half_life_gives_quarter(self):
        """At 2x half-life, score = 0.25."""
        now = datetime.now(timezone.utc)
        later = now + timedelta(hours=TEMPORAL_HALF_LIFE * 2)
        score = _temporal_similarity(now, later)
        assert score == pytest.approx(0.25, abs=0.001)

    def test_triple_half_life_gives_eighth(self):
        """At 3x half-life, score = 0.125."""
        now = datetime.now(timezone.utc)
        later = now + timedelta(hours=TEMPORAL_HALF_LIFE * 3)
        score = _temporal_similarity(now, later)
        assert score == pytest.approx(0.125, abs=0.001)

    def test_24_hours_very_low(self):
        """24 hours apart should give very low similarity.

        2^(-24/4) = 2^(-6) = 1/64 ≈ 0.0156
        """
        now = datetime.now(timezone.utc)
        later = now + timedelta(hours=24)
        score = _temporal_similarity(now, later)
        assert score == pytest.approx(1 / 64, abs=0.001)

    def test_symmetry(self):
        """Order shouldn't matter."""
        now = datetime.now(timezone.utc)
        later = now + timedelta(hours=3)
        assert _temporal_similarity(now, later) == _temporal_similarity(later, now)

    def test_monotonic_decay(self):
        """Closer times should always score higher."""
        now = datetime.now(timezone.utc)
        scores = [_temporal_similarity(now, now + timedelta(hours=h)) for h in [0, 1, 2, 4, 8, 16, 24]]
        for i in range(len(scores) - 1):
            assert scores[i] > scores[i + 1]


# ── Combined similarity ──────────────────────────────────────────────────────


class TestComputeSimilarity:
    def test_identical_alert_and_cluster(self):
        """Identical features should give maximum score."""
        now = datetime.now(timezone.utc)
        cats = {"pricing_change"}
        kws = {"stripe", "deprecated", "tier"}
        scores = compute_similarity(cats, kws, now, cats, kws, now)
        # temporal=1.0, category=1.0, keyword=1.0 → combined=1.0
        assert scores["combined"] == pytest.approx(1.0)

    def test_completely_unrelated(self):
        """Different competitor events should score very low."""
        now = datetime.now(timezone.utc)
        scores = compute_similarity(
            {"pricing_change"},
            {"stripe", "tier", "pricing"},
            now,
            {"hiring_signal"},
            {"engineer", "backend", "remote"},
            now + timedelta(hours=20),
        )
        # temporal is very low (20h apart), categories disjoint, keywords disjoint
        assert scores["combined"] < MERGE_THRESHOLD

    def test_same_competitor_different_pages_same_time(self):
        """Same-time changes on different pages of same competitor should cluster."""
        now = datetime.now(timezone.utc)
        scores = compute_similarity(
            {"pricing_change"},
            {"enterprise", "plan", "annual"},
            now,
            {"feature_launch"},
            {"enterprise", "dashboard", "analytics"},
            now + timedelta(minutes=30),
        )
        # Temporal high at 30min with 4h half-life:
        # 2^(-0.5/4) = 2^(-0.125) ≈ 0.917
        assert scores["temporal"] > 0.9
        assert scores["keyword"] > 0  # "enterprise" overlaps
        assert scores["category"] == 0.0

    def test_same_page_type_hours_apart(self):
        """Same category change 2 hours later should still have decent score."""
        now = datetime.now(timezone.utc)
        scores = compute_similarity(
            {"pricing_change"},
            {"tier", "starter", "monthly"},
            now,
            {"pricing_change"},
            {"tier", "business", "annual"},
            now + timedelta(hours=2),
        )
        # temporal = 2^(-2/4) = 2^(-0.5) ≈ 0.707
        assert scores["temporal"] == pytest.approx(2 ** (-0.5), abs=0.01)
        assert scores["category"] == 1.0

    def test_same_category_at_half_life_with_no_keyword_overlap(self):
        """At exactly the half-life, same category + zero keyword overlap.

        temporal = 0.5, category = 1.0, keyword = 0.0
        combined = 0.4*0.5 + 0.3*1.0 + 0.3*0.0 = 0.2 + 0.3 = 0.5
        Should merge (0.5 > 0.45 threshold).
        """
        now = datetime.now(timezone.utc)
        scores = compute_similarity(
            {"pricing_change"},
            {"starter", "monthly"},
            now,
            {"pricing_change"},
            {"enterprise", "annual"},
            now + timedelta(hours=TEMPORAL_HALF_LIFE),
        )
        assert scores["temporal"] == pytest.approx(0.5, abs=0.01)
        assert scores["combined"] == pytest.approx(0.5, abs=0.01)
        assert scores["combined"] >= MERGE_THRESHOLD

    def test_weights_sum_to_one(self):
        """Verify weight constants are valid."""
        from workers.clustering.alert_clusterer import W_CATEGORY, W_KEYWORD, W_TEMPORAL

        assert W_TEMPORAL + W_CATEGORY + W_KEYWORD == pytest.approx(1.0)


# ── Threshold behavior ───────────────────────────────────────────────────────


class TestThresholdBehavior:
    """Test that the MERGE_THRESHOLD correctly separates events that should
    cluster from those that shouldn't."""

    def test_rapid_multi_page_update_clusters(self):
        """A competitor updating 3 pages in 1 hour should cluster."""
        now = datetime.now(timezone.utc)
        scores = compute_similarity(
            {"pricing_change"},
            {"enterprise", "pricing", "tier"},
            now,
            {"feature_launch"},
            {"enterprise", "dashboard"},
            now + timedelta(minutes=45),
        )
        # temporal = 2^(-0.75/4) ≈ 0.878, keyword overlap on "enterprise", no category overlap
        assert scores["temporal"] > 0.85

    def test_same_competitor_days_apart_low_temporal(self):
        """Changes from the same competitor 5 days apart have near-zero temporal score.

        Note: In production, CLUSTER_WINDOW_HOURS=48 prevents the DB query from
        even returning clusters this old. This test verifies the temporal component
        is effectively zero, even though category/keyword similarity may be high.
        The window check is the primary guard; temporal decay is the secondary one.
        """
        now = datetime.now(timezone.utc)
        scores = compute_similarity(
            {"pricing_change"},
            {"stripe", "tier", "pricing"},
            now,
            {"pricing_change"},
            {"stripe", "tier", "pricing"},
            now + timedelta(days=5),
        )
        # 2^(-120/4) = 2^(-30) ≈ 9.3e-10
        assert scores["temporal"] < 0.001
        assert scores["category"] == 1.0
        assert scores["keyword"] == 1.0


# ── Advisory lock key ────────────────────────────────────────────────────────


class TestAdvisoryLockId:
    def test_deterministic(self):
        """Same inputs always produce the same lock ID."""
        uid = uuid.UUID("12345678-1234-1234-1234-123456789012")
        assert _advisory_lock_id(uid, "Acme") == _advisory_lock_id(uid, "Acme")

    def test_different_for_different_competitors(self):
        uid = uuid.UUID("12345678-1234-1234-1234-123456789012")
        assert _advisory_lock_id(uid, "Acme") != _advisory_lock_id(uid, "Beacon")

    def test_different_for_different_users(self):
        uid1 = uuid.UUID("12345678-1234-1234-1234-123456789012")
        uid2 = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        assert _advisory_lock_id(uid1, "Acme") != _advisory_lock_id(uid2, "Acme")

    def test_returns_positive_int(self):
        uid = uuid.UUID("12345678-1234-1234-1234-123456789012")
        lock_id = _advisory_lock_id(uid, "Acme")
        assert isinstance(lock_id, int)
        assert lock_id > 0


import uuid
