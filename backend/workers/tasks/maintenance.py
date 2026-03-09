from workers.celery_app import celery_app


@celery_app.task(name="workers.tasks.maintenance.cleanup_old_snapshots", queue="default")
def cleanup_old_snapshots(days: int = 90) -> dict:
    """Delete snapshots older than the specified number of days."""
    # TODO: Implement in Milestone 3
    return {"deleted_snapshots": 0, "deleted_diffs": 0, "deleted_analyses": 0}


@celery_app.task(name="workers.tasks.maintenance.cleanup_deleted_monitors", queue="default")
def cleanup_deleted_monitors() -> dict:
    """Hard delete monitors that were soft-deleted more than 30 days ago."""
    # TODO: Implement in Milestone 3
    return {"deleted_monitors": 0, "deleted_mongo_docs": 0}
