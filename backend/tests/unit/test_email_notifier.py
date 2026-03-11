"""Tests for email notifier."""

from unittest.mock import MagicMock, patch

import pytest

from workers.notifier.base import NotificationPayload, NotifierError
from workers.notifier.email_notifier import (
    SEVERITY_COLORS,
    EmailNotifier,
    _build_html_email,
    _build_plain_text,
)


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


class TestBuildHtmlEmail:
    """Test HTML email generation."""

    def test_contains_severity_in_header(self, payload):
        html = _build_html_email(payload)
        assert "HIGH" in html

    def test_contains_summary(self, payload):
        html = _build_html_email(payload)
        assert payload.summary in html

    def test_contains_competitor_name(self, payload):
        html = _build_html_email(payload)
        assert "Example Corp" in html

    def test_contains_severity_color(self, payload):
        html = _build_html_email(payload)
        assert SEVERITY_COLORS["high"] in html

    def test_contains_view_details_button(self, payload):
        html = _build_html_email(payload)
        assert "View Details" in html
        assert f"{payload.dashboard_url}/alerts/{payload.alert_id}" in html

    def test_no_dashboard_url_skips_button(self):
        payload_no_url = NotificationPayload(
            alert_id="test",
            monitor_name="Test",
            competitor_name="Test",
            url="https://example.com",
            page_type="pricing",
            severity="medium",
            summary="Test summary",
            categories=["other"],
            dashboard_url=None,
        )
        html = _build_html_email(payload_no_url)
        assert "View Details" not in html

    def test_null_competitor_shows_unknown(self):
        payload = NotificationPayload(
            alert_id="test",
            monitor_name="Test",
            competitor_name=None,
            url="https://example.com",
            page_type="pricing",
            severity="medium",
            summary="Test",
            categories=["other"],
        )
        html = _build_html_email(payload)
        assert "Unknown Competitor" in html

    def test_is_valid_html(self, payload):
        html = _build_html_email(payload)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html


class TestBuildPlainText:
    """Test plain text email generation."""

    def test_contains_severity(self, payload):
        text = _build_plain_text(payload)
        assert "[HIGH]" in text

    def test_contains_summary(self, payload):
        text = _build_plain_text(payload)
        assert payload.summary in text

    def test_contains_url(self, payload):
        text = _build_plain_text(payload)
        assert payload.url in text

    def test_contains_monitor_name(self, payload):
        text = _build_plain_text(payload)
        assert payload.monitor_name in text

    def test_contains_categories(self, payload):
        text = _build_plain_text(payload)
        assert "pricing_change" in text


class TestEmailNotifier:
    """Test SendGrid email delivery."""

    @patch("workers.notifier.email_notifier.settings")
    def test_send_success(self, mock_settings, payload):
        mock_settings.sendgrid_api_key = "test-key"
        mock_settings.sendgrid_from_email = "alerts@test.com"

        notifier = EmailNotifier()

        with patch("sendgrid.SendGridAPIClient") as MockSG:
            mock_sg = MagicMock()
            MockSG.return_value = mock_sg
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_sg.send.return_value = mock_response

            result = notifier.send(payload, email_address="user@test.com")

        assert result is True
        mock_sg.send.assert_called_once()

    @patch("workers.notifier.email_notifier.settings")
    def test_send_no_email_raises(self, mock_settings, payload):
        mock_settings.sendgrid_api_key = "test-key"
        notifier = EmailNotifier()

        with pytest.raises(NotifierError) as exc_info:
            notifier.send(payload)
        assert exc_info.value.is_retryable is False

    @patch("workers.notifier.email_notifier.settings")
    def test_send_no_api_key_raises(self, mock_settings, payload):
        mock_settings.sendgrid_api_key = ""
        notifier = EmailNotifier()

        with pytest.raises(NotifierError) as exc_info:
            notifier.send(payload, email_address="user@test.com")
        assert "SendGrid API key" in str(exc_info.value)

    @patch("workers.notifier.email_notifier.settings")
    def test_send_server_error_retryable(self, mock_settings, payload):
        mock_settings.sendgrid_api_key = "test-key"
        mock_settings.sendgrid_from_email = "alerts@test.com"

        notifier = EmailNotifier()

        with patch("sendgrid.SendGridAPIClient") as MockSG:
            mock_sg = MagicMock()
            MockSG.return_value = mock_sg
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.body = "Server Error"
            mock_sg.send.return_value = mock_response

            with pytest.raises(NotifierError) as exc_info:
                notifier.send(payload, email_address="user@test.com")
            assert exc_info.value.is_retryable is True

    @patch("workers.notifier.email_notifier.settings")
    def test_send_client_error_not_retryable(self, mock_settings, payload):
        mock_settings.sendgrid_api_key = "test-key"
        mock_settings.sendgrid_from_email = "alerts@test.com"

        notifier = EmailNotifier()

        with patch("sendgrid.SendGridAPIClient") as MockSG:
            mock_sg = MagicMock()
            MockSG.return_value = mock_sg
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.body = "Bad Request"
            mock_sg.send.return_value = mock_response

            with pytest.raises(NotifierError) as exc_info:
                notifier.send(payload, email_address="user@test.com")
            assert exc_info.value.is_retryable is False

    @patch("workers.notifier.email_notifier.settings")
    def test_send_test_method(self, mock_settings):
        mock_settings.sendgrid_api_key = "test-key"
        mock_settings.sendgrid_from_email = "alerts@test.com"

        notifier = EmailNotifier()

        with patch("sendgrid.SendGridAPIClient") as MockSG:
            mock_sg = MagicMock()
            MockSG.return_value = mock_sg
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_sg.send.return_value = mock_response

            result = notifier.send_test(email_address="user@test.com")
        assert result is True


class TestSeverityColors:
    """Test severity color mapping."""

    def test_all_severities_have_colors(self):
        for severity in ["critical", "high", "medium", "low"]:
            assert severity in SEVERITY_COLORS

    def test_colors_are_hex(self):
        for color in SEVERITY_COLORS.values():
            assert color.startswith("#")
            assert len(color) == 7
