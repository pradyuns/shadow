from workers.celery_app import celery_app


@celery_app.task(
    name="workers.tasks.notifications.send_notifications",
    queue="analysis",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def send_notifications(self, alert_id: str) -> dict:  # type: ignore[no-untyped-def]
    """Send notifications for an alert via configured channels."""
    # TODO: Implement in Milestone 3
    return {"slack_sent": False, "email_sent": False}


@celery_app.task(
    name="workers.tasks.notifications.send_daily_digest",
    queue="analysis",
    max_retries=2,
    default_retry_delay=30,
)
def send_daily_digest() -> dict:
    """Aggregate pending digest items and send consolidated notifications."""
    # TODO: Implement in Milestone 3
    return {"digests_sent": 0}
