"""Firecrawl scraper — uses the Firecrawl API for bot-protected sites.

Firecrawl handles anti-bot bypass, JavaScript rendering, and returns clean
content. We request HTML format (not markdown) because our existing
extract_text() pipeline expects HTML input.

The SDK returns a Document Pydantic model with typed fields (.html, .markdown,
.metadata, etc.). See https://docs.firecrawl.dev/sdks/python

Usage:
- As automatic fallback when primary scraper returns bot-detection pages
- As primary scraper for monitors with use_firecrawl=True
"""

import time

import structlog

from app.config import settings
from workers.scraper.base import BaseScraper, ScraperError, ScrapeResult

logger = structlog.get_logger()


class FirecrawlScraper(BaseScraper):
    """Scraper using Firecrawl API for bot-protected and JS-heavy sites."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.firecrawl_api_key
        if not self._api_key:
            raise ScraperError(
                "Firecrawl API key not configured",
                url="",
                is_retryable=False,
            )

    def fetch(self, url: str, timeout_seconds: int = 30, css_selector: str | None = None) -> ScrapeResult:
        """Fetch a URL via Firecrawl API and return raw HTML.

        Args:
            url: The URL to fetch.
            timeout_seconds: Maximum time to wait (passed to Firecrawl as ms).
            css_selector: Optional CSS selector — passed to Firecrawl as
                          include_tags for server-side filtering.

        Returns:
            ScrapeResult with the HTML content from Firecrawl.

        Raises:
            ScraperError: If the Firecrawl API call fails.
        """
        from firecrawl import FirecrawlApp

        client = FirecrawlApp(api_key=self._api_key)
        start_ms = time.monotonic()

        # Build keyword arguments for the scrape call
        scrape_kwargs: dict = {
            "formats": ["html"],
            "timeout": timeout_seconds * 1000,  # Firecrawl expects milliseconds (min 1000)
            "only_main_content": True,  # Strip navs, footers, headers for cleaner content
            "block_ads": True,  # Block ads and cookie popups
        }

        # Pass CSS selector through as include_tags for server-side filtering
        if css_selector:
            scrape_kwargs["include_tags"] = [css_selector]

        try:
            # Response is a firecrawl.v2.types.Document (Pydantic model)
            response = client.scrape(url, **scrape_kwargs)
            duration_ms = int((time.monotonic() - start_ms) * 1000)

            # Document has typed fields: .html, .markdown, .raw_html, .metadata, etc.
            raw_html = response.html or ""

            if not raw_html:
                # Fall back to markdown wrapped in HTML for extract_text() pipeline
                markdown = response.markdown or ""
                if markdown:
                    raw_html = f"<html><body><pre>{markdown}</pre></body></html>"

            # Extract real HTTP status from metadata when available
            http_status = 200
            if response.metadata:
                meta = response.metadata if isinstance(response.metadata, dict) else response.metadata.model_dump()
                http_status = meta.get("statusCode", meta.get("status_code", 200))

            logger.info(
                "firecrawl_scrape_complete",
                url=url,
                duration_ms=duration_ms,
                content_length=len(raw_html),
                http_status=http_status,
            )

            return ScrapeResult(
                url=url,
                raw_html=raw_html,
                http_status=http_status,
                render_method="firecrawl",
                fetch_duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            error_msg = str(e)

            # Detect rate limiting (HTTP 429) and payment errors (HTTP 402)
            is_rate_limited = "429" in error_msg or "rate" in error_msg.lower()
            is_payment = "402" in error_msg or "payment" in error_msg.lower()

            logger.warning(
                "firecrawl_scrape_error",
                url=url,
                duration_ms=duration_ms,
                error=error_msg[:500],
                is_rate_limited=is_rate_limited,
                is_payment_error=is_payment,
            )

            raise ScraperError(
                f"Firecrawl error for {url}: {error_msg[:300]}",
                url=url,
                is_retryable=is_rate_limited,
            )
