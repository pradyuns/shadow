import re
from datetime import datetime, timedelta, timezone

import pytest

from workers.scraper.adaptive_noise_learning import (
    _build_candidate_pattern,
    _extract_replacement_pairs,
    _safeguard_block_reason,
    summarize_monitor_patterns,
)


def test_extract_replacement_pairs():
    diff = """--- previous
+++ current
@@ -1,3 +1,3 @@
-Last updated: March 12
+Last updated: March 13
 Pricing page"""
    pairs = _extract_replacement_pairs(diff)
    assert pairs == [("Last updated: March 12", "Last updated: March 13")]


def test_build_candidate_pattern_from_recurring_structure():
    candidate = _build_candidate_pattern("Last updated: March 12", "Last updated: March 13")
    assert candidate is not None
    assert "{var}" in candidate.template
    assert candidate.similarity > 0.8

    assert re.match(candidate.pattern, "Last updated: March 25")
    assert re.match(candidate.pattern, "Last   updated:   March 31")


def test_safeguard_blocks_price_and_competitor_terms():
    price_reason = _safeguard_block_reason(
        "Enterprise plan: $99 per month",
        "Enterprise plan: $129 per month",
        "Acme Corp",
    )
    assert price_reason is not None

    competitor_reason = _safeguard_block_reason(
        "Acme release notes updated",
        "Acme release notes revised",
        "Acme Corp",
    )
    assert competitor_reason is not None


def test_summarize_monitor_patterns_rolls_up_confidence_and_weekly_impact():
    now = datetime.now(timezone.utc)
    docs = [
        {
            "is_active": True,
            "manual_review_required": False,
            "confidence": 0.9,
            "stats": {
                "total_lines_filtered": 25,
                "recent_filter_events": [{"at": now - timedelta(days=1), "count": 7}],
            },
        },
        {
            "is_active": False,
            "manual_review_required": True,
            "confidence": 0.6,
            "stats": {
                "total_lines_filtered": 5,
                "recent_filter_events": [{"at": now - timedelta(days=10), "count": 8}],
            },
        },
    ]
    summary = summarize_monitor_patterns(docs, now=now)
    assert summary["learned_patterns"] == 2
    assert summary["active_patterns"] == 1
    assert summary["manual_review_patterns"] == 1
    assert summary["total_lines_filtered"] == 30
    assert summary["lines_filtered_7d"] == 7
    assert summary["avg_confidence"] == pytest.approx(0.75)
