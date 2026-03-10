"""Slack notifier using Block Kit for rich, structured alert messages.

Why Block Kit over plain text:
- Structured layout (header, sections, fields, buttons) is scannable in busy channels
- Severity emoji in the header gives instant visual signal
- "View Details" button links directly to the alert in our dashboard
- Fields layout compactly shows metadata (page type, categories)

Why webhooks over Slack API:
- Webhooks are simpler (one POST, no OAuth flow)
- No bot token management or scope configuration
- User pastes their webhook URL and it just works
- Sufficient for alert-only use case (no conversations/reactions needed)
"""

import httpx
import structlog

from workers.notifier.base import BaseNotifier, NotificationPayload, NotifierError

logger = structlog.get_logger()

# Severity → emoji mapping for visual scanning in Slack
SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
}


class SlackNotifier(BaseNotifier):
    """Send notifications via Slack webhook."""

    def __init__(self):
        self._client = httpx.Client(timeout=10.0)

    def send(self, payload: NotificationPayload, **channel_config) -> bool:
        webhook_url = channel_config.get("slack_webhook_url")
        if not webhook_url:
            raise NotifierError("No Slack webhook URL configured", channel="slack", is_retryable=False)

        emoji = SEVERITY_EMOJI.get(payload.severity, "⚪")
        competitor = payload.competitor_name or "Unknown Competitor"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {payload.severity.upper()}: Change on {competitor}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": payload.summary,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Page Type:* {payload.page_type}"},
                    {"type": "mrkdwn", "text": f"*Monitor:* {payload.monitor_name}"},
                    {"type": "mrkdwn", "text": f"*Categories:* {', '.join(payload.categories)}"},
                    {"type": "mrkdwn", "text": f"*URL:* <{payload.url}|View Page>"},
                ],
            },
        ]

        # Add "View Details" button if dashboard URL is available
        if payload.dashboard_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Details"},
                        "url": f"{payload.dashboard_url}/alerts/{payload.alert_id}",
                        "style": "primary",
                    }
                ],
            })

        slack_payload = {
            "text": f"{emoji} [{payload.severity.upper()}] Change detected on {competitor} ({payload.page_type})",
            "blocks": blocks,
        }

        try:
            response = self._client.post(webhook_url, json=slack_payload)

            if response.status_code == 200 and response.text == "ok":
                logger.info("slack_notification_sent", alert_id=payload.alert_id)
                return True
            else:
                logger.warning(
                    "slack_notification_failed",
                    status=response.status_code,
                    body=response.text[:200],
                )
                raise NotifierError(
                    f"Slack returned {response.status_code}: {response.text[:200]}",
                    channel="slack",
                    is_retryable=response.status_code >= 500,
                )

        except httpx.TimeoutException as e:
            raise NotifierError(f"Slack webhook timeout: {e}", channel="slack", is_retryable=True)
        except httpx.ConnectError as e:
            raise NotifierError(f"Slack webhook connection error: {e}", channel="slack", is_retryable=True)

    def send_test(self, **channel_config) -> bool:
        """Send a test message to verify the webhook works."""
        test_payload = NotificationPayload(
            alert_id="test",
            monitor_name="Test Monitor",
            competitor_name="Test Competitor",
            url="https://example.com",
            page_type="homepage",
            severity="medium",
            summary="This is a test notification from Competitor Intelligence Monitor. If you see this, Slack notifications are working correctly! 🎉",
            categories=["other"],
        )
        return self.send(test_payload, **channel_config)
