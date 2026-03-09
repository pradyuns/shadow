from workers.celery_app import celery_app


@celery_app.task(name="workers.tasks.scraping.initiate_scrape_cycle", queue="default")
def initiate_scrape_cycle(batch_size: int = 20) -> dict:
    """Query all active monitors due for checking and dispatch scrape tasks."""
    # TODO: Implement in Milestone 3
    return {"monitors_queued": 0, "batches": 0}


@celery_app.task(
    name="workers.tasks.scraping.scrape_single_url",
    queue="scraper",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    soft_time_limit=60,
    time_limit=90,
    rate_limit="10/m",
)
def scrape_single_url(self, monitor_id: str) -> dict:  # type: ignore[no-untyped-def]
    """Fetch a single URL, store snapshot, dispatch diff task."""
    # TODO: Implement in Milestone 3
    return {"monitor_id": monitor_id, "snapshot_id": None, "status": "pending"}
