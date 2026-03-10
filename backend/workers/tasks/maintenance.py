"""Maintenance tasks — cleanup old data and soft-deleted monitors.

Key decisions:
- TTL-based cleanup for MongoDB documents (snapshots, diffs, analyses)
  rather than capped collections. Capped collections can't be indexed well
  and delete in insertion order, not by age.
- Soft-deleted monitors get 30-day grace period before hard delete.
  This allows users to restore accidentally deleted monitors while
  still eventually cleaning up abandoned data.
- CASCADE in PostgreSQL handles alerts/notification_settings automatically
  when a monitor is hard-deleted. We only need to clean MongoDB manually.
"""

from datetime import datetime, timedelta, timezone

import structlog

from app.config import settings
from workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="workers.tasks.maintenance.cleanup_old_snapshots", queue="default")
def cleanup_old_snapshots(days: int | None = None) -> dict:
    """Delete snapshots older than the specified number of days.

    Also cleans up orphaned diffs and analyses that reference deleted snapshots.
    """
    from app.db.mongodb_sync import get_sync_mongo_db

    mongo_db = get_sync_mongo_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days or settings.snapshot_ttl_days)

    try:
        # Delete old snapshots
        snapshot_result = mongo_db.snapshots.delete_many({"created_at": {"$lt": cutoff}})

        # Delete old diffs (use diff_ttl_days for potentially longer retention)
        diff_cutoff = datetime.now(timezone.utc) - timedelta(days=settings.diff_ttl_days)
        diff_result = mongo_db.diffs.delete_many({"created_at": {"$lt": diff_cutoff}})

        # Delete old analyses
        analysis_cutoff = datetime.now(timezone.utc) - timedelta(days=settings.analysis_ttl_days)
        analysis_result = mongo_db.analyses.delete_many({"created_at": {"$lt": analysis_cutoff}})

        logger.info(
            "cleanup_complete",
            deleted_snapshots=snapshot_result.deleted_count,
            deleted_diffs=diff_result.deleted_count,
            deleted_analyses=analysis_result.deleted_count,
        )

        return {
            "deleted_snapshots": snapshot_result.deleted_count,
            "deleted_diffs": diff_result.deleted_count,
            "deleted_analyses": analysis_result.deleted_count,
        }

    except Exception as e:
        logger.error("cleanup_error", error=str(e), exc_info=True)
        return {"error": str(e)}


@celery_app.task(name="workers.tasks.maintenance.cleanup_deleted_monitors", queue="default")
def cleanup_deleted_monitors() -> dict:
    """Hard delete monitors that were soft-deleted more than 30 days ago.

    For each expired monitor:
    1. Delete all MongoDB documents (snapshots, diffs, analyses) by monitor_id
    2. Hard-delete the PostgreSQL row (CASCADE removes alerts, settings)

    Safe to re-run (idempotent): deleting already-deleted docs is a no-op.
    """
    from sqlalchemy import delete, select

    from app.db.mongodb_sync import get_sync_mongo_db
    from app.db.postgres_sync import get_sync_db
    from app.models.monitor import Monitor

    db = get_sync_db()
    mongo_db = get_sync_mongo_db()

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.deleted_monitor_retention_days)

    try:
        # Find monitors past the retention period
        result = db.execute(
            select(Monitor).where(
                Monitor.deleted_at.isnot(None),
                Monitor.deleted_at < cutoff,
            )
        )
        monitors_to_delete = list(result.scalars().all())

        if not monitors_to_delete:
            return {"deleted_monitors": 0, "deleted_mongo_docs": 0}

        total_mongo_deleted = 0
        monitors_deleted = 0

        for monitor in monitors_to_delete:
            mid = str(monitor.id)

            # Clean up MongoDB documents for this monitor
            snap_del = mongo_db.snapshots.delete_many({"monitor_id": mid}).deleted_count
            diff_del = mongo_db.diffs.delete_many({"monitor_id": mid}).deleted_count
            analysis_del = mongo_db.analyses.delete_many({"monitor_id": mid}).deleted_count
            total_mongo_deleted += snap_del + diff_del + analysis_del

            # Hard-delete the PostgreSQL row (CASCADE handles alerts, etc.)
            db.execute(delete(Monitor).where(Monitor.id == monitor.id))
            monitors_deleted += 1

            logger.info(
                "monitor_hard_deleted",
                monitor_id=mid,
                mongo_docs_deleted=snap_del + diff_del + analysis_del,
            )

        db.commit()

        logger.info(
            "cleanup_deleted_monitors_complete",
            monitors_deleted=monitors_deleted,
            mongo_docs_deleted=total_mongo_deleted,
        )

        return {
            "deleted_monitors": monitors_deleted,
            "deleted_mongo_docs": total_mongo_deleted,
        }

    except Exception as e:
        db.rollback()
        logger.error("cleanup_deleted_monitors_error", error=str(e), exc_info=True)
        return {"error": str(e)}

    finally:
        db.close()
