from workers.celery_app import celery_app


@celery_app.task(
    name="workers.tasks.diffing.compute_diff",
    queue="analysis",
    max_retries=2,
    default_retry_delay=5,
)
def compute_diff(monitor_id: str, snapshot_id: str) -> dict:
    """Compute diff between latest two snapshots for a monitor."""
    # TODO: Implement in Milestone 3
    return {"diff_id": None, "has_changes": False, "is_baseline": False}
