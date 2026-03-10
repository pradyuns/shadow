"""Base notifier interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NotificationPayload:
    """Standardized payload for all notification channels."""

    alert_id: str
    monitor_name: str
    competitor_name: str | None
    url: str
    page_type: str
    severity: str
    summary: str
    categories: list[str]
    dashboard_url: str | None = None


class NotifierError(Exception):
    """Raised when notification delivery fails."""

    def __init__(self, message: str, channel: str, is_retryable: bool = True):
        super().__init__(message)
        self.channel = channel
        self.is_retryable = is_retryable


class BaseNotifier(ABC):
    """Abstract base for notification channels."""

    @abstractmethod
    def send(self, payload: NotificationPayload, **channel_config) -> bool:
        """Send a notification.

        Args:
            payload: The notification content.
            **channel_config: Channel-specific config (webhook URL, email address, etc.)

        Returns:
            True if sent successfully.

        Raises:
            NotifierError on failure.
        """
        ...

    @abstractmethod
    def send_test(self, **channel_config) -> bool:
        """Send a test notification to verify channel configuration."""
        ...
