from workers.celery_app import celery_app


@celery_app.task(
    name="workers.tasks.analysis.classify_significance",
    queue="analysis",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    rate_limit="20/m",
)
def classify_significance(self, diff_id: str) -> dict:  # type: ignore[no-untyped-def]
    """Classify the significance of a diff using Claude API."""
    # TODO: Implement in Milestone 3
    return {"analysis_id": None, "significance": None, "alert_id": None}
