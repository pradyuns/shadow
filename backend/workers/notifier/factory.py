"""Notifier factory — returns the right notifier for each channel.

Same pattern as the scraper factory:
- Task code doesn't know/care which channel it's sending to
- Adding new channels (e.g., Discord, PagerDuty) = new class + factory entry
"""

from workers.notifier.base import BaseNotifier
from workers.notifier.email_notifier import EmailNotifier
from workers.notifier.slack_notifier import SlackNotifier

_slack_notifier: SlackNotifier | None = None
_email_notifier: EmailNotifier | None = None


def get_notifier(channel: str) -> BaseNotifier:
    """Return the notifier for the given channel.

    Args:
        channel: "slack" or "email"

    Returns:
        A notifier instance.

    Raises:
        ValueError: If the channel is not supported.
    """
    global _slack_notifier, _email_notifier

    if channel == "slack":
        if _slack_notifier is None:
            _slack_notifier = SlackNotifier()
        return _slack_notifier
    elif channel == "email":
        if _email_notifier is None:
            _email_notifier = EmailNotifier()
        return _email_notifier
    else:
        raise ValueError(f"Unsupported notification channel: {channel}")
