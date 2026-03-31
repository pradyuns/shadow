"""HTTP scraper using httpx for pages that don't require JavaScript rendering.

Why httpx over requests:
- Built-in connection pooling and HTTP/2 support
- Better timeout granularity (connect, read, write, pool timeouts)
- Clean redirect following with max_redirects
- Same API for sync and async, future-proofing if we move to async workers
"""

import time

import httpx
import structlog

from workers.scraper.base import BaseScraper, ScraperError, ScrapeResult

logger = structlog.get_logger()

# Rotate user agents to reduce bot detection.
# A single static UA would be fingerprinted quickly by WAFs.
USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    ("Mozilla/5.0 (X11; Linux x86_64) " "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
]

_ua_index = 0


def _get_user_agent() -> str:
    global _ua_index
    ua = USER_AGENTS[_ua_index % len(USER_AGENTS)]
    _ua_index += 1
    return ua


class HttpScraper(BaseScraper):
    """Lightweight HTTP scraper for static pages."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            follow_redirects=True,
            max_redirects=5,
            timeout=httpx.Timeout(30.0, connect=10.0),
            # Don't verify SSL in scraper — some competitor sites have
            # expired certs but we still want their content.
            verify=True,
        )

    def fetch(self, url: str, timeout_seconds: int = 30, css_selector: str | None = None) -> ScrapeResult:
        start_ms = time.monotonic()
        try:
            response = self._client.get(
                url,
                headers={
                    "User-Agent": _get_user_agent(),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                },
                timeout=timeout_seconds,
            )
            duration_ms = int((time.monotonic() - start_ms) * 1000)

            logger.info(
                "http_scrape_complete",
                url=url,
                status=response.status_code,
                duration_ms=duration_ms,
                content_length=len(response.text),
            )

            return ScrapeResult(
                url=url,
                raw_html=response.text,
                http_status=response.status_code,
                render_method="httpx",
                fetch_duration_ms=duration_ms,
                final_url=str(response.url) if str(response.url) != url else None,
            )

        except httpx.TimeoutException as e:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            logger.warning("http_scrape_timeout", url=url, duration_ms=duration_ms, error=str(e))
            raise ScraperError(f"Timeout fetching {url}: {e}", url=url, is_retryable=True)

        except httpx.ConnectError as e:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            logger.warning("http_scrape_connect_error", url=url, error=str(e))
            raise ScraperError(f"Connection error for {url}: {e}", url=url, is_retryable=True)

        except httpx.HTTPStatusError as e:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            # 4xx errors are not retryable (page doesn't exist, forbidden, etc.)
            # 5xx are retryable (server issues)
            is_retryable = e.response.status_code >= 500
            raise ScraperError(
                f"HTTP {e.response.status_code} for {url}",
                url=url,
                is_retryable=is_retryable,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            logger.error("http_scrape_unexpected_error", url=url, error=str(e), exc_info=True)
            raise ScraperError(f"Unexpected error fetching {url}: {e}", url=url, is_retryable=True)

    def close(self) -> None:
        self._client.close()
