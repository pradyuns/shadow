"""Notification tasks — deliver alerts via Slack and email.

Pipeline position: scrape → diff → classify → **notify**

Key decisions:
- Each channel is tried independently (Slack failure doesn't block email)
- Digest mode queues alerts for later batch delivery
- Idempotency via notified_at flag — if already set, skip
- Test notifications bypass suppression/severity checks
"""

from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from workers.celery_app import celery_app
from workers.classifier.schemas import SEVERITY_ORDER
from workers.notifier.base import NotificationPayload, NotifierError
from workers.notifier.factory import get_notifier

logger = structlog.get_logger()


@celery_app.task(
    name="workers.tasks.notifications.send_notifications",
    queue="analysis",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def send_notifications(self, alert_id: str) -> dict:
    """Send notifications for an alert via all configured channels.

    Checks each user notification setting:
    - Is the channel enabled?
    - Does the alert severity meet the min_severity threshold?
    - Is digest mode on? → queue instead of sending immediately
    """
    from app.db.mongodb_sync import get_sync_mongo_db
    from app.db.postgres_sync import get_sync_db
    from app.models.alert import Alert
    from app.models.monitor import Monitor
    from app.models.notification_setting import NotificationSetting

    db = get_sync_db()

    try:
        # Load alert
        alert = db.execute(select(Alert).where(Alert.id == alert_id)).scalar_one_or_none()
        if not alert:
            logger.error("notify_alert_not_found", alert_id=alert_id)
            return {"error": "alert_not_found"}

        # Idempotency: skip if already notified
        if alert.notified_at is not None:
            logger.info("notify_skipped_already_sent", alert_id=alert_id)
            return {"slack_sent": alert.notified_via_slack, "email_sent": alert.notified_via_email}

        # Load monitor for context
        monitor = db.execute(select(Monitor).where(Monitor.id == alert.monitor_id)).scalar_one_or_none()
        if not monitor:
            logger.error("notify_monitor_not_found", monitor_id=str(alert.monitor_id))
            return {"error": "monitor_not_found"}

        # Load user notification settings
        settings_result = db.execute(
            select(NotificationSetting).where(NotificationSetting.user_id == alert.user_id)
        )
        user_settings = list(settings_result.scalars().all())

        if not user_settings:
            logger.info("notify_no_settings", alert_id=alert_id, user_id=str(alert.user_id))
            return {"slack_sent": False, "email_sent": False, "reason": "no_settings"}

        # Build payload
        payload = NotificationPayload(
            alert_id=str(alert.id),
            monitor_name=monitor.name,
            competitor_name=monitor.competitor_name,
            url=monitor.url,
            page_type=monitor.page_type,
            severity=alert.severity,
            summary=alert.summary,
            categories=alert.categories if isinstance(alert.categories, list) else [],
        )

        alert_severity_order = SEVERITY_ORDER.get(alert.severity, 0)
        slack_sent = False
        email_sent = False
        errors = []

        for setting in user_settings:
            if not setting.is_enabled:
                continue

            # Check severity threshold
            min_severity_order = SEVERITY_ORDER.get(setting.min_severity, 0)
            if alert_severity_order < min_severity_order:
                logger.debug(
                    "notify_below_threshold",
                    channel=setting.channel,
                    alert_severity=alert.severity,
                    min_severity=setting.min_severity,
                )
                continue

            # Digest mode: queue for later
            if setting.digest_mode:
                mongo_db = get_sync_mongo_db()
                mongo_db.digest_queue.update_one(
                    {
                        "user_id": str(alert.user_id),
                        "channel": setting.channel,
                        "digest_hour_utc": setting.digest_hour_utc or 9,
                    },
                    {
                        "$push": {"alert_ids": str(alert.id)},
                        "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
                    },
                    upsert=True,
                )
                logger.info("notify_queued_for_digest", channel=setting.channel, alert_id=alert_id)
                continue

            # Send immediately
            try:
                notifier = get_notifier(setting.channel)
                channel_config = {
                    "slack_webhook_url": setting.slack_webhook_url,
                    "email_address": setting.email_address,
                }
                notifier.send(payload, **channel_config)

                if setting.channel == "slack":
                    slack_sent = True
                elif setting.channel == "email":
                    email_sent = True

            except NotifierError as e:
                errors.append(f"{setting.channel}: {e}")
                logger.warning("notify_channel_failed", channel=setting.channel, error=str(e))
                if e.is_retryable and self.request.retries < self.max_retries:
                    raise self.retry(exc=e, countdown=10 * (2 ** self.request.retries))

        # Update alert notification status
        alert.notified_via_slack = slack_sent
        alert.notified_via_email = email_sent
        alert.notified_at = datetime.now(timezone.utc)
        if errors:
            alert.notification_error = "; ".join(errors)[:500]
        db.commit()

        logger.info(
            "notifications_sent",
            alert_id=alert_id,
            slack=slack_sent,
            email=email_sent,
            errors=len(errors),
        )

        return {"slack_sent": slack_sent, "email_sent": email_sent}

    except Exception as e:
        logger.error("notify_error", alert_id=alert_id, error=str(e), exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10 * (2 ** self.request.retries))
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    name="workers.tasks.notifications.send_daily_digest",
    queue="analysis",
    max_retries=2,
    default_retry_delay=30,
)
def send_daily_digest() -> dict:
    """Aggregate pending digest items and send consolidated notifications.

    Runs hourly from Beat. Checks digest_queue for entries matching the
    current hour, groups alerts, sends one consolidated message per user/channel.
    """
    from app.db.mongodb_sync import get_sync_mongo_db
    from app.db.postgres_sync import get_sync_db
    from app.models.alert import Alert
    from app.models.monitor import Monitor
    from app.models.notification_setting import NotificationSetting

    mongo_db = get_sync_mongo_db()
    db = get_sync_db()
    current_hour = datetime.now(timezone.utc).hour

    try:
        # Find digest entries for the current hour
        pending_digests = list(mongo_db.digest_queue.find({
            "digest_hour_utc": current_hour,
        }))

        if not pending_digests:
            return {"digests_sent": 0}

        digests_sent = 0

        for digest_entry in pending_digests:
            alert_ids = digest_entry.get("alert_ids", [])
            if not alert_ids:
                mongo_db.digest_queue.delete_one({"_id": digest_entry["_id"]})
                continue

            user_id = digest_entry["user_id"]
            channel = digest_entry["channel"]

            # Load alerts
            alerts = list(db.execute(
                select(Alert).where(Alert.id.in_(alert_ids))
            ).scalars().all())

            if not alerts:
                mongo_db.digest_queue.delete_one({"_id": digest_entry["_id"]})
                continue

            # Build digest summary
            lines = [f"📊 **Daily Digest** — {len(alerts)} alert(s)\n"]
            for alert in alerts:
                monitor = db.execute(
                    select(Monitor).where(Monitor.id == alert.monitor_id)
                ).scalar_one_or_none()
                monitor_name = monitor.name if monitor else "Unknown"
                lines.append(f"• [{alert.severity.upper()}] {monitor_name}: {alert.summary[:100]}")

            digest_text = "\n".join(lines)

            # Load channel config
            setting = db.execute(
                select(NotificationSetting).where(
                    NotificationSetting.user_id == user_id,
                    NotificationSetting.channel == channel,
                )
            ).scalar_one_or_none()

            if setting:
                try:
                    notifier = get_notifier(channel)
                    payload = NotificationPayload(
                        alert_id="digest",
                        monitor_name="Multiple monitors",
                        competitor_name=None,
                        url="",
                        page_type="digest",
                        severity="medium",
                        summary=digest_text,
                        categories=["other"],
                    )
                    notifier.send(payload, slack_webhook_url=setting.slack_webhook_url, email_address=setting.email_address)
                    digests_sent += 1
                except Exception as e:
                    logger.warning("digest_send_failed", user_id=user_id, channel=channel, error=str(e))

            # Clean up
            mongo_db.digest_queue.delete_one({"_id": digest_entry["_id"]})

        logger.info("daily_digest_complete", digests_sent=digests_sent)
        return {"digests_sent": digests_sent}

    finally:
        db.close()


@celery_app.task(
    name="workers.tasks.notifications.send_test_notification",
    queue="analysis",
)
def send_test_notification(user_id: str, channel: str) -> dict:
    """Send a test notification to verify channel configuration."""
    from app.db.postgres_sync import get_sync_db
    from app.models.notification_setting import NotificationSetting

    db = get_sync_db()
    try:
        setting = db.execute(
            select(NotificationSetting).where(
                NotificationSetting.user_id == user_id,
                NotificationSetting.channel == channel,
            )
        ).scalar_one_or_none()

        if not setting:
            return {"user_id": user_id, "channel": channel, "sent": False, "error": "no_setting"}

        notifier = get_notifier(channel)
        notifier.send_test(
            slack_webhook_url=setting.slack_webhook_url,
            email_address=setting.email_address,
        )

        logger.info("test_notification_sent", user_id=user_id, channel=channel)
        return {"user_id": user_id, "channel": channel, "sent": True}

    except Exception as e:
        logger.error("test_notification_failed", user_id=user_id, channel=channel, error=str(e))
        return {"user_id": user_id, "channel": channel, "sent": False, "error": str(e)}

    finally:
        db.close()
