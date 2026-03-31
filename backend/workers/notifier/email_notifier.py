"""Email notifier using SendGrid.

Why SendGrid over raw SMTP:
- Deliverability: SendGrid handles SPF/DKIM/DMARC, reputation management
- No SMTP server to manage (connection pooling, TLS, bounce handling)
- Simple REST API via their Python SDK
- Built-in analytics (open/click tracking) if needed later
- Free tier covers alert volume for small-medium deployments

Why Jinja2 templates:
- Separates email layout from business logic
- Templates can be updated without code changes
- Standard in Python web ecosystem, already a FastAPI transitive dep
"""

from typing import Any

import structlog

from app.config import settings
from workers.notifier.base import BaseNotifier, NotificationPayload, NotifierError

logger = structlog.get_logger()

# Severity → color for email styling
SEVERITY_COLORS = {
    "critical": "#DC2626",  # Red
    "high": "#EA580C",  # Orange
    "medium": "#CA8A04",  # Yellow
    "low": "#2563EB",  # Blue
}


def _build_html_email(payload: NotificationPayload) -> str:
    """Build an HTML email body.

    Using inline HTML rather than Jinja2 templates initially for simplicity.
    Can be moved to .html template files when designs stabilize.
    """
    color = SEVERITY_COLORS.get(payload.severity, "#6B7280")
    competitor = payload.competitor_name or "Unknown Competitor"
    categories_str = ", ".join(payload.categories)
    details_button_html = ""
    if payload.dashboard_url:
        details_button_html = (
            '<div style="margin-top: 24px;">'
            f'<a href="{payload.dashboard_url}/alerts/{payload.alert_id}" '
            f'style="display: inline-block; background-color: {color}; color: white; '
            'padding: 10px 20px; border-radius: 6px; text-decoration: none; font-size: 14px;">'
            "View Details</a></div>"
        )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin: 0; padding: 20px; background-color: #f5f5f5;">
  <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px;
    overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
    <div style="background-color: {color}; color: white; padding: 20px 24px;">
      <h1 style="margin: 0; font-size: 18px;">{payload.severity.upper()}: Change Detected</h1>
      <p style="margin: 8px 0 0; opacity: 0.9; font-size: 14px;">{competitor} &mdash; {payload.page_type}</p>
    </div>
    <div style="padding: 24px;">
      <p style="font-size: 15px; line-height: 1.6; color: #374151; margin-top: 0;">{payload.summary}</p>
      <table style="width: 100%; font-size: 13px; color: #6B7280; border-collapse: collapse;">
        <tr>
          <td style="padding: 8px 0; border-top: 1px solid #E5E7EB;"><strong>Monitor</strong></td>
          <td style="padding: 8px 0; border-top: 1px solid #E5E7EB;">{payload.monitor_name}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; border-top: 1px solid #E5E7EB;"><strong>Page Type</strong></td>
          <td style="padding: 8px 0; border-top: 1px solid #E5E7EB;">{payload.page_type}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; border-top: 1px solid #E5E7EB;"><strong>Categories</strong></td>
          <td style="padding: 8px 0; border-top: 1px solid #E5E7EB;">{categories_str}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; border-top: 1px solid #E5E7EB;"><strong>URL</strong></td>
          <td style="padding: 8px 0; border-top: 1px solid #E5E7EB;">
            <a href="{payload.url}" style="color: #2563EB;">{payload.url}</a>
          </td>
        </tr>
      </table>
      {details_button_html}
    </div>
    <div style="padding: 16px 24px; background-color: #F9FAFB; font-size: 12px;
      color: #9CA3AF; border-top: 1px solid #E5E7EB;">
      Sent by Competitor Intelligence Monitor
    </div>
  </div>
</body>
</html>"""


def _build_plain_text(payload: NotificationPayload) -> str:
    """Build a plain-text fallback for email clients that don't support HTML."""
    competitor = payload.competitor_name or "Unknown Competitor"
    return f"""[{payload.severity.upper()}] Change Detected on {competitor}

{payload.summary}

Monitor: {payload.monitor_name}
Page Type: {payload.page_type}
Categories: {', '.join(payload.categories)}
URL: {payload.url}

{'View details: ' + payload.dashboard_url + '/alerts/' + payload.alert_id if payload.dashboard_url else ''}
---
Sent by Competitor Intelligence Monitor"""


class EmailNotifier(BaseNotifier):
    """Send notifications via SendGrid email."""

    def send(self, payload: NotificationPayload, **channel_config: Any) -> bool:
        email_address = channel_config.get("email_address")
        if not email_address:
            raise NotifierError("No email address configured", channel="email", is_retryable=False)

        if not settings.sendgrid_api_key:
            raise NotifierError("SendGrid API key not configured", channel="email", is_retryable=False)

        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Content, Email, Mail, To

        competitor = payload.competitor_name or "Unknown"
        subject = f"[{payload.severity.upper()}] Change detected on {competitor} - {payload.page_type}"

        message = Mail(
            from_email=Email(settings.sendgrid_from_email),
            to_emails=To(email_address),
            subject=subject,
        )

        # Add both HTML and plain text content
        message.content = [
            Content("text/plain", _build_plain_text(payload)),
            Content("text/html", _build_html_email(payload)),
        ]

        try:
            sg = SendGridAPIClient(settings.sendgrid_api_key)
            response = sg.send(message)

            if response.status_code in (200, 201, 202):
                logger.info("email_notification_sent", alert_id=payload.alert_id, to=email_address)
                return True
            else:
                logger.warning(
                    "email_notification_failed",
                    status=response.status_code,
                    body=response.body,
                )
                raise NotifierError(
                    f"SendGrid returned {response.status_code}",
                    channel="email",
                    is_retryable=response.status_code >= 500,
                )

        except NotifierError:
            raise
        except Exception as e:
            logger.error("email_send_error", error=str(e), exc_info=True)
            raise NotifierError(f"Email send failed: {e}", channel="email", is_retryable=True)

    def send_test(self, **channel_config: Any) -> bool:
        """Send a test email to verify configuration."""
        test_payload = NotificationPayload(
            alert_id="test",
            monitor_name="Test Monitor",
            competitor_name="Test Competitor",
            url="https://example.com",
            page_type="homepage",
            severity="medium",
            summary=(
                "This is a test notification from Competitor Intelligence Monitor. "
                "If you received this email, your notification settings are configured correctly!"
            ),
            categories=["other"],
        )
        return self.send(test_payload, **channel_config)
