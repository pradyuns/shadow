"""Alert suppression logic — prevents notification spam.

Three rules, checked in order:
1. Same-summary: suppress if similar summary sent for this monitor in last 24h
2. Severity-based: suppress if same-or-lower severity already sent in last 24h
3. Oscillation: suppress if page is flip-flopping between states

Why suppress at alert creation, not notification delivery?
- Suppressed alerts are never created, saving PostgreSQL storage
- The analysis is still stored in MongoDB (with suppression reason) for auditing
- Users can see suppressed analyses in the dashboard if they dig in
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from workers.classifier.schemas import SEVERITY_ORDER

logger = structlog.get_logger()

# How many recent text hashes to check for oscillation patterns
OSCILLATION_WINDOW = 6
# Minimum flip-flops to trigger oscillation detection (A→B→A = 1 flip)
OSCILLATION_THRESHOLD = 2


def _normalize_summary(summary: str) -> str:
    """Normalize a summary for near-duplicate comparison.

    Strips numbers, dates, and extra whitespace so that
    "Pricing changed from $10 to $15" and "Pricing changed from $12 to $18"
    are considered the same alert type.
    """
    text = summary.lower()
    # Remove numbers (prices, percentages, counts)
    text = re.sub(r"\d+\.?\d*%?", "", text)
    # Remove dates in various formats
    text = re.sub(r"\d{4}[-/]\d{2}[-/]\d{2}", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _check_same_summary(db: Session, monitor_id: str, summary: str, hours: int = 24) -> dict[str, Any]:
    """Check if a similar alert was already sent for this monitor recently."""
    from app.models.alert import Alert

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    normalized_new = _normalize_summary(summary)

    result = db.execute(
        select(Alert.summary).where(
            Alert.monitor_id == monitor_id,
            Alert.created_at >= cutoff,
        )
    )
    recent_summaries = [row[0] for row in result.all()]

    for existing_summary in recent_summaries:
        if _normalize_summary(existing_summary) == normalized_new:
            return {
                "suppressed": True,
                "reason": f"Similar alert sent within last {hours}h",
            }

    return {"suppressed": False}


def _check_severity_escalation(db: Session, monitor_id: str, severity: str, hours: int = 24) -> dict[str, Any]:
    """Check if a same-or-higher severity alert was already sent recently.

    Only notify if the new alert's severity EXCEEDS the highest recent one.
    This prevents "death by a thousand medium alerts" while still escalating
    when something more important happens.
    """
    from app.models.alert import Alert

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    new_order = SEVERITY_ORDER.get(severity, 0)

    result = db.execute(
        select(Alert.severity).where(
            Alert.monitor_id == monitor_id,
            Alert.created_at >= cutoff,
        )
    )
    recent_severities = [row[0] for row in result.all()]

    if not recent_severities:
        return {"suppressed": False}

    max_recent_order = max(SEVERITY_ORDER.get(s, 0) for s in recent_severities)

    if new_order <= max_recent_order:
        recent_max = max(recent_severities, key=lambda sev: SEVERITY_ORDER.get(sev, 0))
        return {
            "suppressed": True,
            "reason": f"Severity {severity} does not exceed recent max ({recent_max})",
        }

    return {"suppressed": False}


def _check_oscillation(mongo_db: Any, monitor_id: str) -> dict[str, Any]:
    """Detect if a page is oscillating between two states.

    Looks at the last N text hashes. If it alternates (A, B, A, B, ...),
    the page is likely serving different content from different CDN nodes
    or running an A/B test. We suppress until the pattern breaks.
    """
    cursor = mongo_db.snapshots.find(
        {"monitor_id": monitor_id},
        {"text_hash": 1},
        sort=[("created_at", -1)],
        limit=OSCILLATION_WINDOW,
    )
    hashes = [doc["text_hash"] for doc in cursor if "text_hash" in doc]

    if len(hashes) < 4:
        return {"suppressed": False}

    # Check for alternating pattern: A, B, A, B, ...
    unique_hashes = set(hashes)
    if len(unique_hashes) != 2:
        return {"suppressed": False}

    # Count transitions between the two states
    flips = sum(1 for i in range(1, len(hashes)) if hashes[i] != hashes[i - 1])

    if flips >= OSCILLATION_THRESHOLD * 2:  # Each full oscillation = 2 flips
        reason = (
            f"Page oscillating between {len(unique_hashes)} states " f"({flips} flips in last {len(hashes)} snapshots)"
        )
        return {
            "suppressed": True,
            "reason": reason,
        }

    return {"suppressed": False}


# run suppression rules cheapest-first: summary → severity → oscillation
def should_suppress_alert(
    db: Session,
    mongo_db: Any,
    monitor_id: str,
    summary: str,
    severity: str,
) -> dict[str, Any]:
    """Run all suppression rules. Returns first match or no suppression.

    Rules are ordered by cost (cheapest first):
    1. Same-summary (PostgreSQL query, fast)
    2. Severity escalation (PostgreSQL query, fast)
    3. Oscillation detection (MongoDB query, slightly heavier)

    Returns:
        {"suppressed": bool, "reason": str | None}
    """
    # Rule 1: Same-summary
    result = _check_same_summary(db, monitor_id, summary)
    if result["suppressed"]:
        return result

    # Rule 2: Severity escalation
    result = _check_severity_escalation(db, monitor_id, severity)
    if result["suppressed"]:
        return result

    # Rule 3: Oscillation detection
    result = _check_oscillation(mongo_db, monitor_id)
    if result["suppressed"]:
        return result

    return {"suppressed": False, "reason": None}
