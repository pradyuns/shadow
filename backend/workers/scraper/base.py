"""Base scraper interface defining the contract all scrapers must implement."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ScrapeResult:
    """Result of a single URL scrape."""

    url: str
    raw_html: str
    http_status: int
    render_method: str  # "httpx" or "playwright"
    fetch_duration_ms: int
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    final_url: str | None = None  # After redirects
    error: str | None = None


class BaseScraper(ABC):
    """Abstract base scraper. All scrapers implement fetch()."""

    @abstractmethod
    def fetch(self, url: str, timeout_seconds: int = 30, css_selector: str | None = None) -> ScrapeResult:
        """Fetch a URL and return the raw HTML content.

        Args:
            url: The URL to fetch.
            timeout_seconds: Maximum time to wait for the page.
            css_selector: Optional CSS selector to extract specific element's HTML.

        Returns:
            ScrapeResult with raw HTML and metadata.

        Raises:
            ScraperError: If the fetch fails after retries.
        """
        ...


class ScraperError(Exception):
    """Raised when a scrape fails in an unrecoverable way."""

    def __init__(self, message: str, url: str, is_retryable: bool = True):
        super().__init__(message)
        self.url = url
        self.is_retryable = is_retryable
