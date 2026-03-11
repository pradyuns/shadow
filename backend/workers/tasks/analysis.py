"""Analysis task — classify change significance using Claude API.

Pipeline position: scrape → diff → **classify** → notify

Key decisions:
- Claude tool_use for structured output (not text parsing)
- Idempotency: skip if analysis already exists for this diff_id
- Circuit breaker in claude_client prevents cascading API failures
- Alert suppression prevents notification spam
- Only medium+ significance creates alerts (noise/low silently logged)
"""

import uuid
from datetime import datetime, timezone

import structlog
from bson import ObjectId

from app.config import settings
from workers.celery_app import celery_app
from workers.classifier.schemas import SEVERITY_ORDER

logger = structlog.get_logger()


@celery_app.task(
    name="workers.tasks.analysis.classify_significance",
    queue="analysis",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    rate_limit="20/m",
)
def classify_significance(self, diff_id: str) -> dict:
    """Classify the significance of a diff using Claude API.

    Flow:
    1. Idempotency check
    2. Load diff + monitor metadata
    3. Call Claude → store analysis in MongoDB
    4. If medium+: check suppression → create alert → dispatch notifications
    """
    from sqlalchemy import select

    from app.db.mongodb_sync import get_sync_mongo_db
    from app.db.postgres_sync import get_sync_db
    from app.models.alert import Alert
    from app.models.monitor import Monitor
    from workers.classifier.claude_client import classify_change
    from workers.tasks.suppression import should_suppress_alert

    mongo_db = get_sync_mongo_db()
    db = get_sync_db()

    try:
        # Idempotency
        existing = mongo_db.analyses.find_one({"diff_id": diff_id})
        if existing:
            logger.info("classify_skipped_exists", diff_id=diff_id)
            return {
                "analysis_id": str(existing["_id"]),
                "significance": existing.get("significance_level"),
                "alert_id": existing.get("alert_id"),
            }

        # Load diff
        diff_doc = mongo_db.diffs.find_one({"_id": ObjectId(diff_id)})
        if not diff_doc:
            logger.error("classify_diff_not_found", diff_id=diff_id)
            return {"analysis_id": None, "significance": None, "error": "diff_not_found"}

        monitor_id = diff_doc["monitor_id"]

        # Load monitor
        monitor = db.execute(select(Monitor).where(Monitor.id == monitor_id)).scalar_one_or_none()

        if not monitor:
            logger.error("classify_monitor_not_found", monitor_id=monitor_id)
            return {"analysis_id": None, "significance": None, "error": "monitor_not_found"}

        # Call Claude API
        filtered_diff = diff_doc.get("filtered_diff") or diff_doc.get("unified_diff", "")
        try:
            import anthropic

            result = classify_change(
                filtered_diff=filtered_diff,
                competitor_name=monitor.competitor_name,
                page_type=monitor.page_type,
                url=monitor.url,
            )
        except Exception as e:
            # Retryable API errors
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=5 * (3**self.request.retries))
            result = {
                "classification": {
                    "significance_level": "medium",
                    "summary": f"Classification failed after retries: {e}",
                    "categories": ["other"],
                },
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost_usd": 0.0,
                "claude_model": settings.claude_model,
                "needs_review": True,
                "error": str(e),
            }

        classification = result["classification"]

        # Store analysis in MongoDB
        analysis_doc = {
            "diff_id": diff_id,
            "monitor_id": monitor_id,
            "significance_level": classification["significance_level"],
            "summary": classification["summary"],
            "categories": classification["categories"],
            "claude_model": result["claude_model"],
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_cost_usd": result["total_cost_usd"],
            "needs_review": result["needs_review"],
            "error": result.get("error"),
            "created_at": datetime.now(timezone.utc),
        }
        inserted = mongo_db.analyses.insert_one(analysis_doc)
        analysis_id = str(inserted.inserted_id)

        # Update snapshot status
        mongo_db.snapshots.update_one(
            {"_id": ObjectId(diff_doc["snapshot_after_id"])},
            {"$set": {"status": "classified"}},
        )

        # Update monitor last_change_at
        monitor.last_change_at = datetime.now(timezone.utc)
        db.commit()

        severity = classification["significance_level"]
        logger.info(
            "classification_complete",
            diff_id=diff_id,
            analysis_id=analysis_id,
            significance=severity,
            cost_usd=result["total_cost_usd"],
        )

        # Skip alert for noise/low
        if SEVERITY_ORDER.get(severity, 0) < SEVERITY_ORDER.get("medium", 2):
            return {"analysis_id": analysis_id, "significance": severity, "alert_id": None}

        # Check suppression
        suppression = should_suppress_alert(
            db=db,
            mongo_db=mongo_db,
            monitor_id=monitor_id,
            summary=classification["summary"],
            severity=severity,
        )

        if suppression["suppressed"]:
            logger.info("alert_suppressed", monitor_id=monitor_id, reason=suppression["reason"])
            mongo_db.analyses.update_one(
                {"_id": inserted.inserted_id},
                {"$set": {"alert_suppressed": True, "suppression_reason": suppression["reason"]}},
            )
            return {"analysis_id": analysis_id, "significance": severity, "alert_id": None, "suppressed": True}

        # Create alert
        alert = Alert(
            id=uuid.uuid4(),
            monitor_id=uuid.UUID(monitor_id),
            user_id=monitor.user_id,
            severity=severity,
            summary=classification["summary"],
            categories=classification["categories"],
            diff_id=diff_id,
            analysis_id=analysis_id,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        alert_id = str(alert.id)

        mongo_db.analyses.update_one(
            {"_id": inserted.inserted_id},
            {"$set": {"alert_id": alert_id}},
        )

        logger.info("alert_created", alert_id=alert_id, severity=severity, monitor_id=monitor_id)

        # Dispatch notifications
        from workers.tasks.notifications import send_notifications

        send_notifications.delay(alert_id)

        return {"analysis_id": analysis_id, "significance": severity, "alert_id": alert_id}

    except Exception as e:
        logger.error("classify_error", diff_id=diff_id, error=str(e), exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=5 * (2**self.request.retries))
        return {"analysis_id": None, "significance": None, "error": str(e)}

    finally:
        db.close()
