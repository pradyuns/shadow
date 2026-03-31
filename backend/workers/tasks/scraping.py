"""Scraping tasks — fetch competitor pages and store snapshots.

Architecture:
- initiate_scrape_cycle: Orchestrator querying due monitors, dispatching batches.
  Runs from Beat every 6 hours. Uses Redis lock to prevent overlapping cycles.
- scrape_single_url: Fetches one URL, stores snapshot in MongoDB, updates
  monitor state in PostgreSQL, dispatches compute_diff.

Why .delay() instead of Celery chains:
- Independent retry: if compute_diff fails, scrape_single_url doesn't re-run
- Independent idempotency: each task checks if its work was already done
- Simpler error handling: no chain rollback complexity

Firecrawl fallback:
- If primary scraper returns bot-detection content, automatically retry with Firecrawl
- Monitors with use_firecrawl=True skip the primary scraper entirely
"""

import re
from datetime import datetime, timedelta, timezone

import structlog
from celery import group

from app.config import settings
from workers.celery_app import celery_app

logger = structlog.get_logger()

# Patterns that indicate bot-detection / CAPTCHA pages
BOT_DETECTION_PATTERNS = re.compile(
    r"(robot|captcha|verify you.re human|access denied|blocked|"
    r"unusual traffic|security check|please enable javascript|"
    r"checking your browser|attention required|are you a human)",
    re.IGNORECASE,
)


# heuristic: short text with captcha/block keywords signals bot detection
def _looks_like_bot_detection(extracted_text: str) -> bool:
    """Check if extracted text looks like a bot-detection page.

    Heuristic: very short text AND contains bot-detection keywords.
    Real pages almost always have >100 chars of useful content.
    """
    if len(extracted_text) > 500:
        return False
    return bool(BOT_DETECTION_PATTERNS.search(extracted_text))


@celery_app.task(name="workers.tasks.scraping.initiate_scrape_cycle", queue="default")
def initiate_scrape_cycle(batch_size: int | None = None) -> dict:
    """Query all active monitors due for checking and dispatch scrape tasks.

    Uses a Redis lock to prevent overlapping scrape cycles (e.g., if the
    previous cycle is slow and Beat fires again). Lock has 30-min TTL.
    """
    import redis as redis_lib

    batch_size = batch_size or settings.scrape_batch_size

    # Acquire Redis lock to prevent overlapping cycles
    redis_client = redis_lib.Redis.from_url(settings.redis_url)
    lock = redis_client.lock("scrape_cycle_lock", timeout=1800)

    if not lock.acquire(blocking=False):
        logger.info("scrape_cycle_skipped_lock_held")
        return {"monitors_queued": 0, "batches": 0, "skipped": "lock_held"}

    try:
        from sqlalchemy import select

        from app.db.postgres_sync import get_sync_db
        from app.models.monitor import Monitor

        db = get_sync_db()
        try:
            now = datetime.now(timezone.utc)
            result = db.execute(
                select(Monitor.id)
                .where(
                    Monitor.is_active == True,
                    Monitor.deleted_at.is_(None),
                    Monitor.next_check_at <= now,
                )
                .order_by(Monitor.next_check_at)
            )
            monitor_ids = [str(row[0]) for row in result.all()]
        finally:
            db.close()

        if not monitor_ids:
            logger.info("scrape_cycle_no_monitors_due")
            return {"monitors_queued": 0, "batches": 0}

        # Dispatch in batches to avoid overwhelming the scraper queue
        batches = 0
        for i in range(0, len(monitor_ids), batch_size):
            batch = monitor_ids[i : i + batch_size]
            task_group = group(scrape_single_url.s(mid) for mid in batch)
            task_group.apply_async(queue="scraper")
            batches += 1

        logger.info(
            "scrape_cycle_dispatched",
            monitors=len(monitor_ids),
            batches=batches,
            batch_size=batch_size,
        )

        return {"monitors_queued": len(monitor_ids), "batches": batches}

    finally:
        try:
            lock.release()
        except Exception:
            pass


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
def scrape_single_url(self, monitor_id: str) -> dict:
    """Fetch a single URL, store snapshot in MongoDB, dispatch diff.

    State transitions on the monitor:
    - Start: last_scrape_status = 'running'
    - Success: status='success', next_check_at updated, failures reset
    - Failure: status='failed', consecutive_failures++, auto-pause at 5

    Firecrawl fallback:
    - If monitor.use_firecrawl is True, use Firecrawl as primary scraper
    - Otherwise, use httpx/Playwright and fall back to Firecrawl if bot-detected
    """
    from sqlalchemy import select

    from app.db.mongodb_sync import get_sync_mongo_db
    from app.db.postgres_sync import get_sync_db
    from app.models.monitor import Monitor
    from workers.scraper.base import ScraperError
    from workers.scraper.factory import get_firecrawl_scraper, get_scraper
    from workers.scraper.text_extractor import extract_text

    db = get_sync_db()
    mongo_db = get_sync_mongo_db()

    try:
        # Load monitor
        monitor = db.execute(select(Monitor).where(Monitor.id == monitor_id)).scalar_one_or_none()

        if not monitor:
            logger.warning("scrape_monitor_not_found", monitor_id=monitor_id)
            return {"monitor_id": monitor_id, "status": "not_found"}

        if not monitor.is_active or monitor.deleted_at is not None:
            logger.info("scrape_monitor_inactive", monitor_id=monitor_id)
            return {"monitor_id": monitor_id, "status": "inactive"}

        # Idempotency: skip if scraped within last 30 minutes
        if monitor.last_checked_at:
            minutes_ago = (datetime.now(timezone.utc) - monitor.last_checked_at).total_seconds() / 60
            if minutes_ago < 30:
                logger.info("scrape_skipped_recent", monitor_id=monitor_id, minutes_ago=round(minutes_ago))
                return {"monitor_id": monitor_id, "status": "skipped_recent"}

        # Set status to running
        monitor.last_scrape_status = "running"
        db.commit()

        # Determine which scraper to use
        used_firecrawl = False
        firecrawl_scraper = get_firecrawl_scraper()

        if monitor.use_firecrawl and firecrawl_scraper:
            # Per-monitor override: always use Firecrawl
            scraper = firecrawl_scraper
            used_firecrawl = True
            logger.info("scrape_using_firecrawl_primary", monitor_id=monitor_id)
        else:
            scraper = get_scraper(monitor.render_js)

        # Fetch the page
        result = None
        try:
            result = scraper.fetch(
                url=monitor.url,
                timeout_seconds=settings.scrape_timeout_seconds,
                css_selector=monitor.css_selector,
            )
        except ScraperError as e:
            # If primary scraper failed and Firecrawl is available, try it
            if not used_firecrawl and firecrawl_scraper:
                logger.info(
                    "scrape_primary_failed_trying_firecrawl",
                    monitor_id=monitor_id,
                    primary_error=str(e)[:200],
                )
                try:
                    result = firecrawl_scraper.fetch(
                        url=monitor.url,
                        timeout_seconds=settings.scrape_timeout_seconds,
                        css_selector=monitor.css_selector,
                    )
                    used_firecrawl = True
                except ScraperError:
                    pass  # Fall through to error handling below

            if result is None:
                # All scrapers failed
                monitor.last_scrape_status = "failed"
                monitor.last_scrape_error = str(e)[:500]
                monitor.consecutive_failures += 1
                monitor.next_check_at = datetime.now(timezone.utc) + timedelta(hours=monitor.check_interval_hours)
                db.commit()

                # Auto-pause after 5 consecutive failures
                if monitor.consecutive_failures >= 5:
                    monitor.is_active = False
                    db.commit()
                    logger.warning(
                        "monitor_auto_paused", monitor_id=monitor_id, failures=monitor.consecutive_failures
                    )

                if e.is_retryable and self.request.retries < self.max_retries:
                    raise self.retry(exc=e, countdown=10 * (2**self.request.retries))
                return {"monitor_id": monitor_id, "status": "failed", "error": str(e)}

        # Extract text from HTML
        extraction = extract_text(
            raw_html=result.raw_html,
            css_selector=monitor.css_selector,
            page_type=monitor.page_type,
        )

        # Bot detection fallback: if primary scraper got a CAPTCHA page, retry with Firecrawl
        if (
            not used_firecrawl
            and firecrawl_scraper
            and _looks_like_bot_detection(extraction["extracted_text"])
        ):
            logger.info(
                "scrape_bot_detected_trying_firecrawl",
                monitor_id=monitor_id,
                text_preview=extraction["extracted_text"][:100],
            )
            try:
                result = firecrawl_scraper.fetch(
                    url=monitor.url,
                    timeout_seconds=settings.scrape_timeout_seconds,
                    css_selector=monitor.css_selector,
                )
                extraction = extract_text(
                    raw_html=result.raw_html,
                    css_selector=monitor.css_selector,
                    page_type=monitor.page_type,
                )
                used_firecrawl = True
                logger.info(
                    "scrape_firecrawl_fallback_success",
                    monitor_id=monitor_id,
                    text_length=extraction["text_length"],
                )
            except ScraperError as firecrawl_err:
                logger.warning(
                    "scrape_firecrawl_fallback_failed",
                    monitor_id=monitor_id,
                    error=str(firecrawl_err)[:200],
                )
                # Continue with the original (bot-detected) content

        # Auto-upgrade to Playwright if httpx returned too little content
        if extraction["auto_upgrade_js"] and not monitor.render_js and not used_firecrawl:
            monitor.render_js = True
            logger.info("monitor_auto_upgrade_js", monitor_id=monitor_id)
            monitor.next_check_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Store snapshot in MongoDB
        snapshot_doc = {
            "monitor_id": str(monitor.id),
            "url": monitor.url,
            "raw_html": result.raw_html,
            "extracted_text": extraction["extracted_text"],
            "text_hash": extraction["text_hash"],
            "http_status": result.http_status,
            "render_method": result.render_method,
            "fetch_duration_ms": result.fetch_duration_ms,
            "text_length": extraction["text_length"],
            "status": "extracted",
            "is_baseline": False,
            "created_at": datetime.now(timezone.utc),
        }
        inserted = mongo_db.snapshots.insert_one(snapshot_doc)
        snapshot_id = str(inserted.inserted_id)

        # Update monitor state
        now = datetime.now(timezone.utc)
        monitor.last_scrape_status = "success"
        monitor.last_scrape_error = None
        monitor.last_checked_at = now
        monitor.last_snapshot_id = snapshot_id
        monitor.consecutive_failures = 0
        if not extraction["auto_upgrade_js"]:
            monitor.next_check_at = now + timedelta(hours=monitor.check_interval_hours)
        db.commit()

        logger.info(
            "scrape_complete",
            monitor_id=monitor_id,
            snapshot_id=snapshot_id,
            text_length=extraction["text_length"],
            fetch_ms=result.fetch_duration_ms,
            render_method=result.render_method,
            used_firecrawl=used_firecrawl,
        )

        # Dispatch diff computation
        from workers.tasks.diffing import compute_diff

        compute_diff.delay(monitor_id, snapshot_id)

        return {
            "monitor_id": monitor_id,
            "snapshot_id": snapshot_id,
            "status": "success",
            "text_hash": extraction["text_hash"],
            "render_method": result.render_method,
        }

    except Exception as e:
        try:
            monitor.last_scrape_status = "failed"
            monitor.last_scrape_error = f"Unexpected: {str(e)[:400]}"
            monitor.consecutive_failures += 1
            monitor.next_check_at = datetime.now(timezone.utc) + timedelta(hours=monitor.check_interval_hours)
            db.commit()
        except Exception:
            pass

        logger.error("scrape_unexpected_error", monitor_id=monitor_id, error=str(e), exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10 * (2**self.request.retries))
        return {"monitor_id": monitor_id, "status": "failed", "error": str(e)}

    finally:
        db.close()
