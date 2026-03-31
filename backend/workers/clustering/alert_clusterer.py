"""Online alert clustering — groups related competitor changes into events.

Problem: When a competitor launches a product, they update pricing, changelog,
docs, and hiring pages. This generates 5+ independent alerts. Users should see
one grouped event, not five separate items.

Algorithm: Online single-linkage clustering with exponential time decay.

When a new alert arrives:
1. Extract feature vector: (competitor, timestamp, categories, summary keywords)
2. Query open clusters for the same competitor within the CLUSTER_WINDOW
3. Compute similarity score against each candidate cluster:
   - Temporal proximity:  2^(-hours_diff / TEMPORAL_HALF_LIFE)
   - Category overlap:    Jaccard similarity on category sets
   - Keyword similarity:  Jaccard similarity on extracted keyword sets
   - Combined:            weighted sum of the three components
4. If best score > MERGE_THRESHOLD → add alert to that cluster
5. Else → create a new single-alert cluster

Design decisions:
- Jaccard over cosine: categories and keywords are small sets (3-8 items),
  not high-dimensional vectors. Jaccard is simpler and equally effective here.
- Exponential decay over hard cutoff: a 3-hour-old cluster is "more open" than
  a 40-hour-old cluster. Hard cutoffs create cliff edges where a 24h01m gap
  means no clustering while 23h59m means full clustering.
- Single-linkage (nearest cluster): alerts join the closest cluster, not the
  average of all clusters. This handles chains where alert A is similar to B,
  B is similar to C, but A and C are less similar — they still belong together.
- Online (one-at-a-time): alerts arrive asynchronously from Celery tasks. We
  can't batch-cluster because we don't know when the next alert will arrive.
- Row-level locking: SELECT FOR UPDATE on candidate clusters prevents two
  concurrent workers from both creating new clusters for the same event.
  Advisory locks on the create path prevent TOCTOU races.

Complexity: O(K) per alert where K = number of open clusters for that competitor.
K is typically < 10, so this is effectively O(1) in practice.
"""

import hashlib
import math
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from workers.classifier.schemas import SEVERITY_ORDER

logger = structlog.get_logger()

# ── Tunable parameters ──────────────────────────────────────────────────────
# How far back to look for open clusters to merge into
CLUSTER_WINDOW_HOURS = 48

# True half-life for temporal similarity decay.
# At exactly TEMPORAL_HALF_LIFE hours apart, temporal score = 0.5.
# At 2x half-life, score = 0.25. At 3x, 0.125. Etc.
# Formula: score = 2^(-hours_diff / TEMPORAL_HALF_LIFE)
#        = exp(-hours_diff * ln(2) / TEMPORAL_HALF_LIFE)
TEMPORAL_HALF_LIFE = 4.0

# Precomputed: ln(2) / TEMPORAL_HALF_LIFE
_DECAY_RATE = math.log(2) / TEMPORAL_HALF_LIFE

# Minimum combined similarity to merge into an existing cluster.
# Below this threshold, a new cluster is created.
# Empirically: 0.45 catches same-day product launches without over-merging
# unrelated changes from the same competitor days apart.
MERGE_THRESHOLD = 0.45

# Component weights (must sum to 1.0)
W_TEMPORAL = 0.40
W_CATEGORY = 0.30
W_KEYWORD = 0.30

# Stop words for keyword extraction — common words that don't carry signal
STOP_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "no",
        "so",
        "if",
        "than",
        "too",
        "very",
        "just",
        "about",
        "change",
        "changed",
        "changes",
        "detected",
        "updated",
        "update",
        "page",
        "new",
        "now",
        "added",
        "removed",
    }
)


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from alert summary text.

    Tokenizes, lowercases, removes stop words and short tokens.
    Returns a set for Jaccard comparison.
    """
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    return {t for t in tokens if len(t) > 2 and t not in STOP_WORDS}


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity: |A ∩ B| / |A ∪ B|.

    Returns 0.0 if both sets are empty (no information = no similarity).
    Range: [0.0, 1.0] where 1.0 = identical sets.
    """
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _temporal_similarity(t1: datetime, t2: datetime) -> float:
    """True half-life exponential decay similarity.

    score = 2^(-hours_diff / TEMPORAL_HALF_LIFE)
          = exp(-hours_diff * ln(2) / TEMPORAL_HALF_LIFE)

    Properties:
    - Same time: 1.0
    - TEMPORAL_HALF_LIFE apart: 0.5 (exactly)
    - 2 * TEMPORAL_HALF_LIFE apart: 0.25
    - 3 * TEMPORAL_HALF_LIFE apart: 0.125
    - Monotonically decreasing, never reaches 0
    """
    hours_diff = abs((t1 - t2).total_seconds()) / 3600
    return math.exp(-hours_diff * _DECAY_RATE)


def compute_similarity(
    alert_categories: set[str],
    alert_keywords: set[str],
    alert_time: datetime,
    cluster_categories: set[str],
    cluster_keywords: set[str],
    cluster_time: datetime,
) -> dict[str, float]:
    """Compute weighted similarity between an alert and a cluster.

    Returns dict with component scores and combined score for transparency/debugging.
    """
    temporal = _temporal_similarity(alert_time, cluster_time)
    category = _jaccard(alert_categories, cluster_categories)
    keyword = _jaccard(alert_keywords, cluster_keywords)

    combined = (W_TEMPORAL * temporal) + (W_CATEGORY * category) + (W_KEYWORD * keyword)

    return {
        "combined": combined,
        "temporal": temporal,
        "category": category,
        "keyword": keyword,
    }


def _advisory_lock_id(user_id: uuid.UUID, competitor: str) -> int:
    """Derive a stable int64 advisory lock key from (user_id, competitor).

    PostgreSQL advisory locks use bigint keys. We hash the composite key
    to a 63-bit integer (positive, since pg_advisory_xact_lock takes bigint).
    """
    raw = f"{user_id}:{competitor}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:15], 16)


def assign_to_cluster(db: Session, alert: Any) -> uuid.UUID | None:
    """Assign an alert to an existing cluster or create a new one.

    This is the main entry point called from the analysis task after alert creation.

    Concurrency safety:
    - Candidate clusters are loaded with SELECT FOR UPDATE to prevent two workers
      from simultaneously merging into the same cluster with stale counts.
    - A PostgreSQL transaction-scoped advisory lock on (user_id, competitor_name)
      serializes the "no match → create new cluster" path, preventing two workers
      from each creating a new cluster for the same event.

    Args:
        db: Synchronous SQLAlchemy session (Celery worker context)
        alert: The Alert ORM instance (must have monitor relationship loaded)

    Returns:
        The cluster_id the alert was assigned to, or None on error.
    """
    from app.models.alert_cluster import AlertCluster
    from app.models.monitor import Monitor

    try:
        # Load monitor for competitor_name
        monitor = db.execute(select(Monitor).where(Monitor.id == alert.monitor_id)).scalar_one_or_none()

        if not monitor:
            logger.warning("cluster_monitor_not_found", alert_id=str(alert.id))
            return None

        competitor = (monitor.competitor_name or "").strip()

        # Skip clustering for monitors without a competitor name.
        # Without a real competitor, alerts from unrelated companies would all
        # land in one shared bucket, defeating the purpose of clustering.
        if not competitor:
            logger.info("cluster_skipped_no_competitor", alert_id=str(alert.id))
            return None

        alert_categories = set(alert.categories or [])
        alert_keywords = _extract_keywords(alert.summary)
        alert_time = alert.created_at or datetime.now(timezone.utc)

        # Acquire advisory lock for this (user, competitor) pair.
        # This serializes cluster creation so two concurrent workers can't both
        # see "no matching cluster" and each create a new one.
        # Transaction-scoped: released automatically on commit/rollback.
        lock_id = _advisory_lock_id(alert.user_id, competitor)
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})

        # Query open clusters with row-level locking.
        # FOR UPDATE prevents concurrent reads from getting stale alert_count/severity
        # while we decide whether to merge.
        cutoff = datetime.now(timezone.utc) - timedelta(hours=CLUSTER_WINDOW_HOURS)
        candidates = (
            db.execute(
                select(AlertCluster)
                .where(
                    AlertCluster.user_id == alert.user_id,
                    AlertCluster.competitor_name == competitor,
                    AlertCluster.is_resolved.is_(False),
                    AlertCluster.updated_at >= cutoff,
                )
                .with_for_update()
            )
            .scalars()
            .all()
        )

        best_cluster = None
        best_score = 0.0
        best_breakdown: dict[str, float] | None = None

        for cluster in candidates:
            cluster_categories = set(cluster.categories or [])
            cluster_keywords = set(cluster.summary_keywords or [])
            cluster_time = cluster.updated_at

            scores = compute_similarity(
                alert_categories,
                alert_keywords,
                alert_time,
                cluster_categories,
                cluster_keywords,
                cluster_time,
            )

            if scores["combined"] > best_score:
                best_score = scores["combined"]
                best_cluster = cluster
                best_breakdown = scores

        if best_cluster and best_score >= MERGE_THRESHOLD:
            # ── Merge into existing cluster ──────────────────────────────
            best_cluster.alert_count += 1
            best_cluster.categories = list(set(best_cluster.categories or []) | alert_categories)
            best_cluster.summary_keywords = list(set(best_cluster.summary_keywords or []) | alert_keywords)
            # Escalate severity if new alert is higher
            if SEVERITY_ORDER.get(alert.severity, 0) > SEVERITY_ORDER.get(best_cluster.severity, 0):
                best_cluster.severity = alert.severity
            best_cluster.updated_at = datetime.now(timezone.utc)

            alert.cluster_id = best_cluster.id
            db.commit()
            if best_breakdown is None:
                best_breakdown = {"temporal": 0.0, "category": 0.0, "keyword": 0.0}

            logger.info(
                "alert_clustered_existing",
                alert_id=str(alert.id),
                cluster_id=str(best_cluster.id),
                score=round(best_score, 3),
                temporal=round(best_breakdown["temporal"], 3),
                category=round(best_breakdown["category"], 3),
                keyword=round(best_breakdown["keyword"], 3),
                cluster_size=best_cluster.alert_count,
            )
            return best_cluster.id

        else:
            # ── Create new cluster ───────────────────────────────────────
            cluster = AlertCluster(
                id=uuid.uuid4(),
                user_id=alert.user_id,
                competitor_name=competitor,
                title=_generate_cluster_title(competitor, alert.categories, alert.summary),
                severity=alert.severity,
                alert_count=1,
                categories=list(alert_categories),
                summary_keywords=list(alert_keywords),
            )
            db.add(cluster)

            alert.cluster_id = cluster.id
            db.commit()

            logger.info(
                "alert_cluster_created",
                alert_id=str(alert.id),
                cluster_id=str(cluster.id),
                competitor=competitor,
                best_candidate_score=round(best_score, 3) if best_score > 0 else None,
            )
            return cluster.id

    except Exception as e:
        logger.error("cluster_assignment_error", alert_id=str(alert.id), error=str(e), exc_info=True)
        db.rollback()
        return None


def _generate_cluster_title(competitor: str, categories: list[str], summary: str) -> str:
    """Generate a human-readable cluster title from the first alert.

    Examples:
    - "Acme Analytics — pricing change"
    - "Beacon AI — feature launch"
    - "Cortex Platform — multiple changes"
    """
    if categories:
        primary = categories[0].replace("_", " ").title()
        return f"{competitor} — {primary}"
    # Fallback: use first few words of summary
    short = " ".join(summary.split()[:6])
    return f"{competitor} — {short}"
