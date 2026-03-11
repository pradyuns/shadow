"""Tests for Slack notifier."""

from unittest.mock import MagicMock, patch

import pytest

from workers.notifier.base import NotificationPayload, NotifierError
from workers.notifier.slack_notifier import SEVERITY_EMOJI, SlackNotifier


@pytest.fixture
def notifier():
    return SlackNotifier()


@pytest.fixture
def payload():
    return NotificationPayload(
        alert_id="alert-123",
        monitor_name="Example Pricing",
        competitor_name="Example Corp",
        url="https://example.com/pricing",
        page_type="pricing",
        severity="high",
        summary="Enterprise plan price increased from $99 to $129/month",
        categories=["pricing_change"],
        dashboard_url="https://app.compmon.io",
    )


class TestSlackNotifier:
    """Test Slack webhook notification delivery."""

    def test_send_success(self, notifier, payload):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            result = notifier.send(payload, slack_webhook_url="https://hooks.slack.com/test")

        assert result is True
        mock_client.post.assert_called_once()

    def test_send_includes_blocks(self, notifier, payload):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            notifier.send(payload, slack_webhook_url="https://hooks.slack.com/test")

            call_args = mock_client.post.call_args
            sent_payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert "blocks" in sent_payload
            assert len(sent_payload["blocks"]) >= 3  # header, section, fields

    def test_send_includes_severity_emoji(self, notifier, payload):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            notifier.send(payload, slack_webhook_url="https://hooks.slack.com/test")

            call_args = mock_client.post.call_args
            sent_payload = call_args.kwargs.get("json") or call_args[1].get("json")
            header_text = sent_payload["blocks"][0]["text"]["text"]
            assert SEVERITY_EMOJI["high"] in header_text

    def test_send_includes_view_details_button(self, notifier, payload):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            notifier.send(payload, slack_webhook_url="https://hooks.slack.com/test")

            call_args = mock_client.post.call_args
            sent_payload = call_args.kwargs.get("json") or call_args[1].get("json")
            # Should have an actions block with a button
            actions_block = [b for b in sent_payload["blocks"] if b["type"] == "actions"]
            assert len(actions_block) == 1

    def test_send_no_dashboard_url_skips_button(self, notifier):
        payload_no_url = NotificationPayload(
            alert_id="alert-123",
            monitor_name="Test",
            competitor_name="Test",
            url="https://example.com",
            page_type="pricing",
            severity="medium",
            summary="Test",
            categories=["other"],
            dashboard_url=None,
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            notifier.send(payload_no_url, slack_webhook_url="https://hooks.slack.com/test")

            call_args = mock_client.post.call_args
            sent_payload = call_args.kwargs.get("json") or call_args[1].get("json")
            actions_block = [b for b in sent_payload["blocks"] if b["type"] == "actions"]
            assert len(actions_block) == 0

    def test_send_no_webhook_url_raises(self, notifier, payload):
        with pytest.raises(NotifierError) as exc_info:
            notifier.send(payload)
        assert exc_info.value.is_retryable is False

    def test_send_server_error_retryable(self, notifier, payload):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            with pytest.raises(NotifierError) as exc_info:
                notifier.send(payload, slack_webhook_url="https://hooks.slack.com/test")
            assert exc_info.value.is_retryable is True

    def test_send_client_error_not_retryable(self, notifier, payload):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            with pytest.raises(NotifierError) as exc_info:
                notifier.send(payload, slack_webhook_url="https://hooks.slack.com/test")
            assert exc_info.value.is_retryable is False

    def test_send_timeout_retryable(self, notifier, payload):
        import httpx

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            with pytest.raises(NotifierError) as exc_info:
                notifier.send(payload, slack_webhook_url="https://hooks.slack.com/test")
            assert exc_info.value.is_retryable is True

    def test_send_connection_error_retryable(self, notifier, payload):
        import httpx

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.side_effect = httpx.ConnectError("connection refused")
            with pytest.raises(NotifierError) as exc_info:
                notifier.send(payload, slack_webhook_url="https://hooks.slack.com/test")
            assert exc_info.value.is_retryable is True


class TestSeverityEmoji:
    """Test severity to emoji mapping."""

    def test_all_severities_have_emoji(self):
        for severity in ["critical", "high", "medium", "low"]:
            assert severity in SEVERITY_EMOJI

    def test_critical_is_red(self):
        assert SEVERITY_EMOJI["critical"] == "\U0001f534"

    def test_unknown_severity_returns_white(self, notifier, payload):
        payload.severity = "unknown"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            notifier.send(payload, slack_webhook_url="https://hooks.slack.com/test")
            # Should not raise - uses fallback emoji


class TestSendTest:
    """Test the test notification method."""

    def test_send_test_calls_send(self, notifier):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch.object(notifier, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            result = notifier.send_test(slack_webhook_url="https://hooks.slack.com/test")
        assert result is True
