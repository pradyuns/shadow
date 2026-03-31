"""Tests for notification tasks."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestSendNotifications:
    @patch("workers.tasks.notifications.get_sync_db")
    def test_alert_not_found(self, mock_pg):
        from workers.tasks.notifications import send_notifications

        db = MagicMock()
        mock_pg.return_value = db
        db.execute.return_value.scalar_one_or_none.return_value = None

        result = send_notifications("alert-1")
        assert result["error"] == "alert_not_found"

    @patch("workers.tasks.notifications.get_sync_db")
    def test_skips_already_notified(self, mock_pg):
        from workers.tasks.notifications import send_notifications

        db = MagicMock()
        mock_pg.return_value = db

        alert = MagicMock()
        alert.notified_at = datetime.now(timezone.utc)
        alert.notified_via_slack = True
        alert.notified_via_email = False
        db.execute.return_value.scalar_one_or_none.return_value = alert

        result = send_notifications("alert-1")
        assert result["slack_sent"] is True
        assert result["email_sent"] is False

    @patch("workers.tasks.notifications.get_notifier")
    @patch("workers.tasks.notifications.get_sync_db")
    def test_sends_slack_notification(self, mock_pg, mock_get_notifier):
        from workers.tasks.notifications import send_notifications

        db = MagicMock()
        mock_pg.return_value = db

        # Alert
        alert = MagicMock()
        alert.id = uuid.uuid4()
        alert.notified_at = None
        alert.monitor_id = uuid.uuid4()
        alert.user_id = uuid.uuid4()
        alert.severity = "critical"
        alert.summary = "Pricing changed"
        alert.categories = ["pricing"]

        # Monitor
        monitor = MagicMock()
        monitor.name = "Test Monitor"
        monitor.competitor_name = "Acme"
        monitor.url = "https://example.com"
        monitor.page_type = "pricing"

        # Notification setting
        setting = MagicMock()
        setting.is_enabled = True
        setting.channel = "slack"
        setting.min_severity = "low"
        setting.digest_mode = False
        setting.slack_webhook_url = "https://hooks.slack.com/test"
        setting.email_address = None

        # DB calls: alert, monitor, settings
        db.execute.return_value.scalar_one_or_none.side_effect = [alert, monitor]
        settings_result = MagicMock()
        settings_result.scalars.return_value.all.return_value = [setting]

        # Override side_effect for the 3 calls
        call_count = [0]
        original_alert = alert
        original_monitor = monitor

        def db_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.scalar_one_or_none.return_value = original_alert
            elif call_count[0] == 2:
                mock_result.scalar_one_or_none.return_value = original_monitor
            else:
                mock_result.scalars.return_value.all.return_value = [setting]
            return mock_result

        db.execute.side_effect = db_execute_side_effect

        # Mock notifier
        notifier = MagicMock()
        mock_get_notifier.return_value = notifier

        result = send_notifications(str(alert.id))
        assert result["slack_sent"] is True
        notifier.send.assert_called_once()

    @patch("workers.tasks.notifications.get_sync_db")
    def test_no_settings_configured(self, mock_pg):
        from workers.tasks.notifications import send_notifications

        db = MagicMock()
        mock_pg.return_value = db

        alert = MagicMock()
        alert.id = uuid.uuid4()
        alert.notified_at = None
        alert.monitor_id = uuid.uuid4()
        alert.user_id = uuid.uuid4()

        monitor = MagicMock()
        monitor.name = "Test"

        call_count = [0]

        def db_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.scalar_one_or_none.return_value = alert
            elif call_count[0] == 2:
                mock_result.scalar_one_or_none.return_value = monitor
            else:
                mock_result.scalars.return_value.all.return_value = []
            return mock_result

        db.execute.side_effect = db_execute_side_effect

        result = send_notifications(str(alert.id))
        assert result["reason"] == "no_settings"

    @patch("workers.tasks.notifications.get_sync_mongo_db")
    @patch("workers.tasks.notifications.get_notifier")
    @patch("workers.tasks.notifications.get_sync_db")
    def test_digest_mode_queues_alert(self, mock_pg, mock_get_notifier, mock_mongo):
        from workers.tasks.notifications import send_notifications

        db = MagicMock()
        mock_pg.return_value = db
        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        alert = MagicMock()
        alert.id = uuid.uuid4()
        alert.notified_at = None
        alert.monitor_id = uuid.uuid4()
        alert.user_id = uuid.uuid4()
        alert.severity = "medium"
        alert.summary = "Change"
        alert.categories = ["other"]

        monitor = MagicMock()
        monitor.name = "Test"
        monitor.competitor_name = "Acme"
        monitor.url = "https://example.com"
        monitor.page_type = "pricing"

        setting = MagicMock()
        setting.is_enabled = True
        setting.channel = "slack"
        setting.min_severity = "low"
        setting.digest_mode = True
        setting.digest_hour_utc = 9
        setting.slack_webhook_url = "https://hooks.slack.com/test"

        call_count = [0]

        def db_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.scalar_one_or_none.return_value = alert
            elif call_count[0] == 2:
                mock_result.scalar_one_or_none.return_value = monitor
            else:
                mock_result.scalars.return_value.all.return_value = [setting]
            return mock_result

        db.execute.side_effect = db_execute_side_effect

        result = send_notifications(str(alert.id))
        mongo_db.digest_queue.update_one.assert_called_once()
        mock_get_notifier.return_value.send.assert_not_called()


class TestSendTestNotification:
    @patch("workers.tasks.notifications.get_notifier")
    @patch("workers.tasks.notifications.get_sync_db")
    def test_send_test_success(self, mock_pg, mock_get_notifier):
        from workers.tasks.notifications import send_test_notification

        db = MagicMock()
        mock_pg.return_value = db

        setting = MagicMock()
        setting.slack_webhook_url = "https://hooks.slack.com/test"
        setting.email_address = None
        db.execute.return_value.scalar_one_or_none.return_value = setting

        notifier = MagicMock()
        mock_get_notifier.return_value = notifier

        result = send_test_notification("user-1", "slack")
        assert result["sent"] is True
        notifier.send_test.assert_called_once()

    @patch("workers.tasks.notifications.get_sync_db")
    def test_send_test_no_setting(self, mock_pg):
        from workers.tasks.notifications import send_test_notification

        db = MagicMock()
        mock_pg.return_value = db
        db.execute.return_value.scalar_one_or_none.return_value = None

        result = send_test_notification("user-1", "slack")
        assert result["sent"] is False
        assert result["error"] == "no_setting"

    @patch("workers.tasks.notifications.get_notifier")
    @patch("workers.tasks.notifications.get_sync_db")
    def test_send_test_error(self, mock_pg, mock_get_notifier):
        from workers.tasks.notifications import send_test_notification

        db = MagicMock()
        mock_pg.return_value = db

        setting = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = setting

        mock_get_notifier.return_value.send_test.side_effect = Exception("Network error")

        result = send_test_notification("user-1", "slack")
        assert result["sent"] is False
        assert "Network error" in result["error"]


class TestSendDailyDigest:
    @patch("workers.tasks.notifications.get_sync_db")
    @patch("workers.tasks.notifications.get_sync_mongo_db")
    def test_no_pending_digests(self, mock_mongo, mock_pg):
        from workers.tasks.notifications import send_daily_digest

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db
        db = MagicMock()
        mock_pg.return_value = db

        mongo_db.digest_queue.find.return_value = []

        result = send_daily_digest()
        assert result["digests_sent"] == 0

    @patch("workers.tasks.notifications.get_notifier")
    @patch("workers.tasks.notifications.get_sync_db")
    @patch("workers.tasks.notifications.get_sync_mongo_db")
    def test_sends_digest(self, mock_mongo, mock_pg, mock_get_notifier):
        from workers.tasks.notifications import send_daily_digest

        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db
        db = MagicMock()
        mock_pg.return_value = db

        # Pending digest entry
        digest_entry = {
            "_id": "digest-1",
            "user_id": "user-1",
            "channel": "slack",
            "alert_ids": ["alert-1"],
            "digest_hour_utc": datetime.now(timezone.utc).hour,
        }
        mongo_db.digest_queue.find.return_value = [digest_entry]

        # Mock alert
        alert = MagicMock()
        alert.severity = "medium"
        alert.summary = "Pricing changed"
        alert.monitor_id = uuid.uuid4()

        alerts_result = MagicMock()
        alerts_result.scalars.return_value.all.return_value = [alert]

        # Mock monitor
        monitor = MagicMock()
        monitor.name = "Test Monitor"

        # Mock setting
        setting = MagicMock()
        setting.slack_webhook_url = "https://hooks.slack.com/test"
        setting.email_address = None

        # DB execute calls: alerts query, monitor query, setting query
        call_count = [0]

        def db_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.scalars.return_value.all.return_value = [alert]
            elif call_count[0] == 2:
                mock_result.scalar_one_or_none.return_value = monitor
            else:
                mock_result.scalar_one_or_none.return_value = setting
            return mock_result

        db.execute.side_effect = db_execute_side_effect

        notifier = MagicMock()
        mock_get_notifier.return_value = notifier

        result = send_daily_digest()
        assert result["digests_sent"] == 1
        notifier.send.assert_called_once()
        mongo_db.digest_queue.delete_one.assert_called()
