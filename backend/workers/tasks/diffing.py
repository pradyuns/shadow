"""Diffing task — compare latest snapshot against the previous one.

Pipeline position: scrape → **diff** → classify → notify

Key decisions:
- Text-level diffing (not HTML): we care about content, not markup
- Noise filtering before Claude: saves 60-80% of API costs
- Idempotency: skip if a diff already exists for this snapshot_after_id
"""

from datetime import datetime, timezone

import structlog
from bson import ObjectId

from workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="workers.tasks.diffing.compute_diff",
    queue="analysis",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def compute_diff(self, monitor_id: str, snapshot_id: str) -> dict:
    """Compute diff between the new snapshot and the previous one.

    Flow:
    1. Idempotency check (diff exists for snapshot?)
    2. Load new + previous snapshot from MongoDB
    3. No previous → mark as baseline, exit
    4. Same text_hash → no change, exit
    5. Compute unified diff
    6. Apply noise filter
    7. If filtered diff empty → noise only, exit
    8. Store diff, dispatch classify_significance
    """
    from sqlalchemy import select

    from app.db.mongodb_sync import get_sync_mongo_db
    from app.db.postgres_sync import get_sync_db
    from app.models.monitor import Monitor
    from workers.differ.text_differ import compute_text_diff
    from workers.scraper.adaptive_noise_learning import (
        get_active_learned_patterns,
        learn_patterns_from_diff,
        record_learned_pattern_usage,
    )
    from workers.scraper.noise_filter import filter_diff

    mongo_db = get_sync_mongo_db()

    try:
        # Idempotency
        existing_diff = mongo_db.diffs.find_one({"snapshot_after_id": snapshot_id})
        if existing_diff:
            logger.info("diff_skipped_exists", monitor_id=monitor_id, snapshot_id=snapshot_id)
            return {
                "diff_id": str(existing_diff["_id"]),
                "has_changes": not existing_diff.get("is_empty_after_filter", True),
                "is_baseline": False,
            }

        # Load new snapshot
        new_snapshot = mongo_db.snapshots.find_one({"_id": ObjectId(snapshot_id)})
        if not new_snapshot:
            logger.error("diff_snapshot_not_found", snapshot_id=snapshot_id)
            return {"diff_id": None, "has_changes": False, "error": "snapshot_not_found"}

        # Find previous snapshot
        prev_snapshot = mongo_db.snapshots.find_one(
            {"monitor_id": monitor_id, "_id": {"$ne": ObjectId(snapshot_id)}},
            sort=[("created_at", -1)],
        )

        # No previous → baseline
        if not prev_snapshot:
            mongo_db.snapshots.update_one(
                {"_id": ObjectId(snapshot_id)},
                {"$set": {"is_baseline": True, "status": "baseline"}},
            )
            logger.info("diff_baseline_snapshot", monitor_id=monitor_id, snapshot_id=snapshot_id)
            return {"diff_id": None, "has_changes": False, "is_baseline": True}

        # Hash comparison — O(1) check before expensive O(n) diff
        if new_snapshot.get("text_hash") == prev_snapshot.get("text_hash"):
            mongo_db.snapshots.update_one(
                {"_id": ObjectId(snapshot_id)},
                {"$set": {"status": "no_change"}},
            )
            logger.info("diff_no_change", monitor_id=monitor_id)
            return {"diff_id": None, "has_changes": False, "is_baseline": False}

        # Load monitor for noise patterns
        db = get_sync_db()
        try:
            monitor = db.execute(select(Monitor).where(Monitor.id == monitor_id)).scalar_one_or_none()
            monitor_noise_patterns = monitor.noise_patterns if monitor else []
            monitor_name = monitor.name if monitor else "unknown"
            if monitor:
                try:
                    learned_noise_patterns = get_active_learned_patterns(mongo_db, monitor_id=str(monitor_id))
                except Exception:
                    learned_noise_patterns = []
                    logger.warning("adaptive_noise_load_failed", monitor_id=monitor_id, exc_info=True)
            else:
                learned_noise_patterns = []
        finally:
            db.close()

        # Compute diff
        text_before = prev_snapshot.get("extracted_text", "")
        text_after = new_snapshot.get("extracted_text", "")
        diff_result = compute_text_diff(text_before, text_after, monitor_name=monitor_name)

        if diff_result.is_identical:
            mongo_db.snapshots.update_one(
                {"_id": ObjectId(snapshot_id)},
                {"$set": {"status": "no_change"}},
            )
            return {"diff_id": None, "has_changes": False, "is_baseline": False}

        # Apply noise filter
        filter_result = filter_diff(
            diff_result.unified_diff,
            monitor_noise_patterns,
            learned_noise_patterns=learned_noise_patterns,
        )

        # Store diff
        diff_doc = {
            "monitor_id": monitor_id,
            "snapshot_before_id": str(prev_snapshot["_id"]),
            "snapshot_after_id": snapshot_id,
            "unified_diff": diff_result.unified_diff,
            "filtered_diff": filter_result.filtered_diff if not filter_result.is_empty_after_filter else None,
            "diff_lines_added": diff_result.lines_added,
            "diff_lines_removed": diff_result.lines_removed,
            "diff_size_bytes": diff_result.diff_size_bytes,
            "noise_lines_removed": filter_result.noise_lines_removed,
            "learned_noise_lines_removed": filter_result.learned_noise_lines_removed,
            "learned_noise_pattern_hits": filter_result.learned_pattern_hits,
            "is_empty_after_filter": filter_result.is_empty_after_filter,
            "created_at": datetime.now(timezone.utc),
        }
        inserted = mongo_db.diffs.insert_one(diff_doc)
        diff_id = str(inserted.inserted_id)

        if filter_result.learned_pattern_hits:
            try:
                record_learned_pattern_usage(
                    mongo_db,
                    monitor_id=str(monitor_id),
                    pattern_hits=filter_result.learned_pattern_hits,
                    diff_id=diff_id,
                    recorded_at=diff_doc["created_at"],
                )
            except Exception:
                logger.warning("adaptive_noise_usage_record_failed", monitor_id=monitor_id, diff_id=diff_id, exc_info=True)

        if monitor:
            try:
                learn_stats = learn_patterns_from_diff(
                    mongo_db,
                    monitor_id=str(monitor.id),
                    monitor_name=monitor.name,
                    user_id=str(monitor.user_id),
                    competitor_name=monitor.competitor_name,
                    diff_id=diff_id,
                    unified_diff=diff_result.unified_diff,
                    observed_at=diff_doc["created_at"],
                )
            except Exception:
                learn_stats = {"error": "adaptive_learning_failed"}
                logger.warning("adaptive_noise_learning_failed", monitor_id=monitor_id, diff_id=diff_id, exc_info=True)
        else:
            learn_stats = {"skipped": "monitor_not_found"}

        new_status = "diffed" if not filter_result.is_empty_after_filter else "no_change"
        mongo_db.snapshots.update_one(
            {"_id": ObjectId(snapshot_id)},
            {"$set": {"status": new_status}},
        )

        logger.info(
            "diff_stored",
            monitor_id=monitor_id,
            diff_id=diff_id,
            lines_added=diff_result.lines_added,
            lines_removed=diff_result.lines_removed,
            noise_removed=filter_result.noise_lines_removed,
            learned_noise_removed=filter_result.learned_noise_lines_removed,
            learned_patterns_matched=len(filter_result.learned_pattern_hits),
            adaptive_learning=learn_stats,
            has_meaningful_changes=not filter_result.is_empty_after_filter,
        )

        # Dispatch classification if meaningful changes
        if not filter_result.is_empty_after_filter:
            from workers.tasks.analysis import classify_significance

            classify_significance.delay(diff_id)

        return {
            "diff_id": diff_id,
            "has_changes": not filter_result.is_empty_after_filter,
            "is_baseline": False,
        }

    except Exception as e:
        logger.error("diff_error", monitor_id=monitor_id, snapshot_id=snapshot_id, error=str(e), exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=5 * (2**self.request.retries))
        return {"diff_id": None, "has_changes": False, "error": str(e)}
