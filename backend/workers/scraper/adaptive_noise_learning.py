"""Adaptive per-monitor noise learning for diff filtering.

Learns recurring structural templates from monitor-specific diff history and
promotes low-risk patterns into active learned regexes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

LEARNED_PATTERNS_COLLECTION = "adaptive_noise_patterns"

MIN_SNAPSHOTS_FOR_LEARNING = 10
MIN_TEMPLATE_SIMILARITY = 0.58
MIN_LITERAL_CHARS = 8
MAX_LINE_LENGTH = 280
MAX_DIFF_IDS_TRACKED = 120
MAX_EXAMPLES_TRACKED = 8
MAX_FILTER_EVENTS_TRACKED = 240
CONFIDENCE_LOOKBACK_DAYS = 60
MIN_SUPPORT_FOR_PROMOTION = 3
MIN_CONFIDENCE_FOR_PROMOTION = 0.78
DECAY_HALF_LIFE_DAYS = 21.0
MIN_DECAY_FOR_ACTIVE = 0.20

PROTECTED_WORDS_BASE = frozenset(
    {
        "price",
        "pricing",
        "plan",
        "plans",
        "tier",
        "tiers",
        "free",
        "enterprise",
        "starter",
        "business",
        "premium",
        "professional",
        "trial",
        "discount",
        "launch",
        "launched",
        "announce",
        "announced",
        "announcement",
        "deprecate",
        "deprecated",
        "deprecation",
        "remove",
        "removed",
        "retire",
        "retired",
        "release",
        "released",
        "introduce",
        "introduced",
    }
)

PRICE_SIGNAL_RE = re.compile(
    r"(\$\s?\d|\d+(?:\.\d+)?\s?%|\b(?:usd|eur|gbp|cad|aud)\b)",
    re.IGNORECASE,
)
ACTION_SIGNAL_RE = re.compile(
    r"\b(launch(?:ed)?|deprecat(?:e|ed|ion)|remove(?:d)?|announce(?:d|ment)?|release(?:d)?)\b",
    re.IGNORECASE,
)

_indexes_ensured = False


@dataclass(frozen=True)
class CandidatePattern:
    pattern: str
    template: str
    similarity: float
    before: str
    after: str


# timezone helpers — ensure all timestamps are utc-aware
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return _utc_now()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_line(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _split_diff_content(line: str) -> str:
    if not line:
        return ""
    return _normalize_line(line[1:])


def _escape_literal_segment(segment: str) -> str:
    parts = []
    for chunk in re.split(r"(\s+)", segment):
        if not chunk:
            continue
        if chunk.isspace():
            if not parts or parts[-1] == r"\s+":
                continue
            parts.append(r"\s+")
            continue
        parts.append(re.escape(chunk))
    return "".join(parts)


def _extract_replacement_pairs(unified_diff: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    pending_removed: list[str] = []

    for line in unified_diff.splitlines():
        if line.startswith("@@"):
            pending_removed.clear()
            continue

        if line.startswith("---") or line.startswith("+++"):
            continue

        if line.startswith("-"):
            content = _split_diff_content(line)
            if content:
                pending_removed.append(content)
            continue

        if line.startswith("+"):
            content = _split_diff_content(line)
            if content and pending_removed:
                before = pending_removed.pop(0)
                pairs.append((before, content))
            continue

        pending_removed.clear()

    return pairs


# build a regex pattern from a before/after line pair using token-level alignment
def _build_candidate_pattern(before: str, after: str) -> CandidatePattern | None:
    if not before or not after or before == after:
        return None
    if len(before) > MAX_LINE_LENGTH or len(after) > MAX_LINE_LENGTH:
        return None

    similarity = SequenceMatcher(None, before, after).ratio()
    if similarity < MIN_TEMPLATE_SIMILARITY:
        return None

    # Token-level matching avoids overfitting to single-character numeric changes
    # like "12 -> 13", which should become one variable span.
    before_tokens = re.findall(r"\S+|\s+", before)
    after_tokens = re.findall(r"\S+|\s+", after)
    matcher = SequenceMatcher(None, before_tokens, after_tokens)

    regex_parts: list[str] = []
    template_parts: list[str] = []
    literal_chars = 0
    variable_spans = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            segment = "".join(before_tokens[i1:i2])
            if not segment:
                continue
            literal = _escape_literal_segment(segment)
            if literal:
                regex_parts.append(literal)
            normalized = _normalize_line(segment)
            if normalized:
                template_parts.append(normalized)
                literal_chars += len(normalized.replace(" ", ""))
            continue

        changed_before = "".join(before_tokens[i1:i2])
        changed_after = "".join(after_tokens[j1:j2])
        if not changed_before and not changed_after:
            continue

        variable_spans += 1
        if not regex_parts or regex_parts[-1] != r".+?":
            regex_parts.append(r".+?")
        if not template_parts or template_parts[-1] != "{var}":
            template_parts.append("{var}")

    if variable_spans == 0 or literal_chars < MIN_LITERAL_CHARS:
        return None

    regex = "^" + "".join(regex_parts) + "$"
    template = " ".join(part for part in template_parts if part).strip()
    if not template:
        template = "{var}"

    return CandidatePattern(
        pattern=regex,
        template=template,
        similarity=similarity,
        before=before,
        after=after,
    )


def _competitor_tokens(competitor_name: str | None) -> set[str]:
    if not competitor_name:
        return set()
    return {token for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", competitor_name.lower()) if len(token) > 2}


def _has_digit_adjacent_business_term(text: str) -> bool:
    lower = text.lower()
    terms = ("tier", "plan", "free", "enterprise", "starter", "pro", "business", "premium")
    for term in terms:
        if re.search(rf"\b{term}\b", lower) and re.search(r"\d", lower):
            return True
    return False


# check if a candidate pattern contains business-critical signals that shouldn't be auto-filtered
def _safeguard_block_reason(before: str, after: str, competitor_name: str | None) -> str | None:
    combined = f"{before} {after}"
    if PRICE_SIGNAL_RE.search(combined):
        return "price_or_percentage_signal"
    if _has_digit_adjacent_business_term(combined):
        return "digit_adjacent_business_term"
    if ACTION_SIGNAL_RE.search(combined):
        return "change_action_word"

    tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", combined.lower()))
    protected = PROTECTED_WORDS_BASE | _competitor_tokens(competitor_name)
    overlap = tokens & protected
    if overlap:
        return f"protected_token:{sorted(overlap)[0]}"
    return None


# exponential decay — patterns not seen recently lose relevance
def _compute_decay_score(last_seen_at: datetime, now: datetime) -> float:
    age_days = max((now - _as_utc(last_seen_at)).total_seconds(), 0.0) / 86400.0
    return 0.5 ** (age_days / DECAY_HALF_LIFE_DAYS)


# weighted confidence score: 45% support ratio, 35% similarity, 20% recency
def _compute_confidence(
    support_count: int,
    avg_similarity: float,
    recent_diff_count: int,
    decay_score: float,
) -> float:
    support_ratio = min(1.0, support_count / max(recent_diff_count, 1))
    confidence = (0.45 * support_ratio) + (0.35 * avg_similarity) + (0.20 * decay_score)
    return round(min(0.995, max(0.0, confidence)), 4)


# sum filter event counts within a rolling window (used by api layer too)
def sum_recent_filter_events(events: list[dict[str, Any]], now: datetime, *, days: int = 7) -> int:
    cutoff = now - timedelta(days=days)
    total = 0
    for event in events:
        ts = event.get("at")
        if not isinstance(ts, datetime):
            continue
        if _as_utc(ts) >= cutoff:
            total += int(event.get("count", 0))
    return total


# check promotion criteria: decay, review flag, support count, confidence
def _is_pattern_active(doc: dict[str, Any], now: datetime) -> tuple[bool, float]:
    last_seen = _as_utc(doc.get("last_seen_at"))
    decay = _compute_decay_score(last_seen, now)
    if decay < MIN_DECAY_FOR_ACTIVE:
        return False, decay
    if doc.get("manual_review_required", False):
        return False, decay
    if doc.get("support_count", 0) < MIN_SUPPORT_FOR_PROMOTION:
        return False, decay
    if float(doc.get("confidence", 0.0)) < MIN_CONFIDENCE_FOR_PROMOTION:
        return False, decay
    return True, decay


def _ensure_indexes(mongo_db: Any) -> None:
    global _indexes_ensured
    if _indexes_ensured:
        return

    collection = mongo_db[LEARNED_PATTERNS_COLLECTION]
    collection.create_index([("monitor_id", 1), ("pattern", 1)], unique=True, name="uq_monitor_pattern")
    collection.create_index([("monitor_id", 1), ("is_active", 1)], name="idx_monitor_active")
    collection.create_index([("monitor_id", 1), ("manual_review_required", 1)], name="idx_monitor_review")
    collection.create_index([("last_seen_at", -1)], name="idx_last_seen")
    _indexes_ensured = True


# return regex strings for all active learned patterns, deactivating decayed ones
def get_active_learned_patterns(mongo_db: Any, monitor_id: str, *, now: datetime | None = None) -> list[str]:
    _ensure_indexes(mongo_db)
    ts = _as_utc(now)
    collection = mongo_db[LEARNED_PATTERNS_COLLECTION]

    docs = list(collection.find({"monitor_id": monitor_id, "is_active": True}, {"pattern": 1, "last_seen_at": 1}))
    patterns: list[str] = []
    for doc in docs:
        last_seen = _as_utc(doc.get("last_seen_at"))
        decay = _compute_decay_score(last_seen, ts)
        if decay < MIN_DECAY_FOR_ACTIVE:
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"is_active": False, "decay_score": decay, "last_updated_at": ts}},
            )
            continue
        pattern = doc.get("pattern")
        if isinstance(pattern, str):
            patterns.append(pattern)
    return patterns


# record how many lines each pattern filtered in a given diff
def record_learned_pattern_usage(
    mongo_db: Any,
    *,
    monitor_id: str,
    pattern_hits: dict[str, int],
    diff_id: str,
    recorded_at: datetime | None = None,
) -> None:
    if not pattern_hits:
        return

    _ensure_indexes(mongo_db)
    ts = _as_utc(recorded_at)
    collection = mongo_db[LEARNED_PATTERNS_COLLECTION]

    for pattern, count in pattern_hits.items():
        if count <= 0:
            continue
        collection.update_one(
            {"monitor_id": monitor_id, "pattern": pattern},
            {
                "$inc": {"stats.total_lines_filtered": int(count)},
                "$set": {"last_matched_at": ts, "last_updated_at": ts},
                "$push": {
                    "stats.recent_filter_events": {
                        "$each": [{"at": ts, "count": int(count), "diff_id": diff_id}],
                        "$slice": -MAX_FILTER_EVENTS_TRACKED,
                    }
                },
            },
        )


# extract replacement pairs from a diff and upsert candidate patterns into mongo
def learn_patterns_from_diff(
    mongo_db: Any,
    *,
    monitor_id: str,
    monitor_name: str,
    user_id: str,
    competitor_name: str | None,
    diff_id: str,
    unified_diff: str,
    observed_at: datetime | None = None,
) -> dict[str, int | str]:
    if not unified_diff.strip():
        return {"candidates": 0, "updated": 0, "promoted": 0, "blocked": 0, "skipped": "empty_diff"}

    _ensure_indexes(mongo_db)
    ts = _as_utc(observed_at)

    snapshot_count = mongo_db.snapshots.count_documents({"monitor_id": monitor_id})
    if snapshot_count < MIN_SNAPSHOTS_FOR_LEARNING:
        return {
            "candidates": 0,
            "updated": 0,
            "promoted": 0,
            "blocked": 0,
            "skipped": "insufficient_snapshot_history",
        }

    recent_diff_count = mongo_db.diffs.count_documents(
        {
            "monitor_id": monitor_id,
            "created_at": {"$gte": ts - timedelta(days=CONFIDENCE_LOOKBACK_DAYS)},
        }
    )

    pairs = _extract_replacement_pairs(unified_diff)
    if not pairs:
        return {"candidates": 0, "updated": 0, "promoted": 0, "blocked": 0, "skipped": "no_replacement_pairs"}

    collection = mongo_db[LEARNED_PATTERNS_COLLECTION]
    processed_patterns: set[str] = set()
    updated = 0
    promoted = 0
    blocked = 0

    for before, after in pairs:
        candidate = _build_candidate_pattern(before, after)
        if not candidate:
            continue
        if candidate.pattern in processed_patterns:
            continue
        processed_patterns.add(candidate.pattern)

        safeguard_reason = _safeguard_block_reason(candidate.before, candidate.after, competitor_name)
        if safeguard_reason:
            blocked += 1

        existing = collection.find_one({"monitor_id": monitor_id, "pattern": candidate.pattern})
        if existing:
            doc = existing
        else:
            doc = {
                "monitor_id": monitor_id,
                "monitor_name": monitor_name,
                "user_id": user_id,
                "competitor_name": competitor_name,
                "pattern": candidate.pattern,
                "template": candidate.template,
                "support_count": 0,
                "avg_similarity": 0.0,
                "confidence": 0.0,
                "decay_score": 1.0,
                "is_active": False,
                "manual_review_required": False,
                "blocked_reason": None,
                "first_seen_at": ts,
                "last_seen_at": ts,
                "last_matched_at": None,
                "promoted_at": None,
                "seen_diff_ids": [],
                "examples": [],
                "stats": {"total_lines_filtered": 0, "recent_filter_events": []},
            }

        was_active = bool(doc.get("is_active", False))
        seen_diff_ids = list(doc.get("seen_diff_ids", []))
        is_new_diff = diff_id not in seen_diff_ids

        if is_new_diff:
            support_count = int(doc.get("support_count", 0))
            avg_similarity = float(doc.get("avg_similarity", 0.0))
            new_support = support_count + 1
            doc["support_count"] = new_support
            doc["avg_similarity"] = ((avg_similarity * support_count) + candidate.similarity) / new_support
            doc["last_seen_at"] = ts
            seen_diff_ids.append(diff_id)
            doc["seen_diff_ids"] = seen_diff_ids[-MAX_DIFF_IDS_TRACKED:]

            examples = list(doc.get("examples", []))
            examples.append(
                {
                    "before": candidate.before,
                    "after": candidate.after,
                    "diff_id": diff_id,
                    "seen_at": ts,
                }
            )
            doc["examples"] = examples[-MAX_EXAMPLES_TRACKED:]

        if safeguard_reason:
            doc["manual_review_required"] = True
            doc["blocked_reason"] = safeguard_reason

        decay_score = _compute_decay_score(_as_utc(doc.get("last_seen_at")), ts)
        doc["decay_score"] = round(decay_score, 4)
        doc["confidence"] = _compute_confidence(
            int(doc.get("support_count", 0)),
            float(doc.get("avg_similarity", 0.0)),
            recent_diff_count,
            decay_score,
        )

        should_activate, _ = _is_pattern_active(doc, ts)
        doc["is_active"] = should_activate
        if should_activate and not was_active:
            doc["promoted_at"] = ts
            promoted += 1
        elif not should_activate and was_active:
            doc["promoted_at"] = doc.get("promoted_at")

        doc["last_updated_at"] = ts

        if "_id" in doc:
            collection.replace_one({"_id": doc["_id"]}, doc)
        else:
            collection.insert_one(doc)

        updated += 1

    return {
        "candidates": len(processed_patterns),
        "updated": updated,
        "promoted": promoted,
        "blocked": blocked,
    }


# aggregate stats across all learned patterns for a single monitor
def summarize_monitor_patterns(
    pattern_docs: list[dict[str, Any]], *, now: datetime | None = None
) -> dict[str, float | int]:
    ts = _as_utc(now)
    if not pattern_docs:
        return {
            "learned_patterns": 0,
            "active_patterns": 0,
            "manual_review_patterns": 0,
            "lines_filtered_7d": 0,
            "total_lines_filtered": 0,
            "avg_confidence": 0.0,
        }

    learned_patterns = len(pattern_docs)
    active_patterns = sum(1 for doc in pattern_docs if doc.get("is_active", False))
    manual_review_patterns = sum(1 for doc in pattern_docs if doc.get("manual_review_required", False))
    total_lines_filtered = sum(int(doc.get("stats", {}).get("total_lines_filtered", 0)) for doc in pattern_docs)
    lines_filtered_7d = sum(
        sum_recent_filter_events(doc.get("stats", {}).get("recent_filter_events", []), ts, days=7)
        for doc in pattern_docs
    )
    avg_confidence = sum(float(doc.get("confidence", 0.0)) for doc in pattern_docs) / learned_patterns

    return {
        "learned_patterns": learned_patterns,
        "active_patterns": active_patterns,
        "manual_review_patterns": manual_review_patterns,
        "lines_filtered_7d": lines_filtered_7d,
        "total_lines_filtered": total_lines_filtered,
        "avg_confidence": round(avg_confidence, 3),
    }
