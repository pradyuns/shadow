"""Playwright scraper for JavaScript-rendered pages.

Why Playwright over Selenium:
- First-class Python support, no external webdriver binary management
- Auto-wait for elements, built-in network idle detection
- Headless by default, lower memory than full Chrome
- Resource blocking API to skip images/fonts/CSS for faster scrapes
- Single binary install via `playwright install chromium`

Architecture: Module-level browser singleton per worker process.
- Browser persists across tasks (expensive to start, ~500ms cold boot)
- Each task opens a new Page, navigates, extracts, closes the Page
- worker_max_tasks_per_child=100 recycles the process, killing the browser
- Crash recovery: if browser disconnects, re-launch on next task
"""

import time
from typing import Any

import structlog

from workers.scraper.base import BaseScraper, ScraperError, ScrapeResult

logger = structlog.get_logger()

# Module-level singleton — survives across Celery tasks in the same worker process.
_playwright: Any | None = None
_browser: Any | None = None

# Resource types to block: saves bandwidth and memory, speeds up scrapes.
# We only care about the DOM text content, not how it looks.
BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "stylesheet"}


def _get_browser() -> Any:
    """Lazily initialize or recover the browser singleton.

    Why lazy init instead of worker_init signal:
    - Not all tasks need Playwright (only render_js=True monitors)
    - Avoids paying the 500ms startup cost for httpx-only batches
    - Signal-based init is fragile with Celery prefork pool
    """
    global _playwright, _browser

    if _browser is not None:
        try:
            # Check if browser is still alive (could have crashed/OOM'd)
            if _browser.is_connected():
                return _browser
            else:
                logger.warning("playwright_browser_disconnected, restarting")
                _cleanup_browser()
        except Exception:
            logger.warning("playwright_browser_check_failed, restarting")
            _cleanup_browser()

    from playwright.sync_api import sync_playwright

    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-gpu",
            "--disable-dev-shm-usage",  # Prevent /dev/shm OOM in Docker
            "--no-sandbox",  # Required in Docker containers
            "--disable-setuid-sandbox",
        ],
    )
    logger.info("playwright_browser_launched")
    return _browser


def _cleanup_browser() -> None:
    """Safely tear down browser and playwright instances."""
    global _playwright, _browser
    try:
        if _browser:
            _browser.close()
    except Exception:
        pass
    try:
        if _playwright:
            _playwright.stop()
    except Exception:
        pass
    _browser = None
    _playwright = None


class PlaywrightScraper(BaseScraper):
    """JS-rendering scraper using headless Chromium via Playwright."""

    def fetch(self, url: str, timeout_seconds: int = 30, css_selector: str | None = None) -> ScrapeResult:
        start_ms = time.monotonic()
        browser = _get_browser()
        page = None

        try:
            # New context per scrape for isolation (cookies, storage)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                java_script_enabled=True,
            )

            # Block heavy resources — we only need the DOM text
            context.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot,css}",
                lambda route: route.abort(),
            )
            context.route(
                "**/*",
                lambda route: (
                    route.abort() if route.request.resource_type in BLOCKED_RESOURCE_TYPES else route.continue_()
                ),
            )

            page = context.new_page()
            timeout_ms = timeout_seconds * 1000

            # Navigate and wait for network to settle.
            # networkidle waits for 500ms with no network requests — good for
            # SPAs that load data after initial HTML. "load" would be too early
            # for React/Vue apps, "domcontentloaded" even earlier.
            response = page.goto(url, wait_until="networkidle", timeout=timeout_ms)

            http_status = response.status if response else 0

            # If a CSS selector is specified, wait for it and extract just that element
            if css_selector:
                try:
                    page.wait_for_selector(css_selector, timeout=10000)
                    element = page.query_selector(css_selector)
                    raw_html = element.inner_html() if element else page.content()
                except Exception:
                    # Selector not found — fall back to full page
                    logger.warning("css_selector_not_found", url=url, selector=css_selector)
                    raw_html = page.content()
            else:
                raw_html = page.content()

            duration_ms = int((time.monotonic() - start_ms) * 1000)

            logger.info(
                "playwright_scrape_complete",
                url=url,
                status=http_status,
                duration_ms=duration_ms,
                content_length=len(raw_html),
            )

            return ScrapeResult(
                url=url,
                raw_html=raw_html,
                http_status=http_status,
                render_method="playwright",
                fetch_duration_ms=duration_ms,
                final_url=page.url if page.url != url else None,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            error_name = type(e).__name__
            logger.warning(
                "playwright_scrape_error",
                url=url,
                error=str(e),
                error_type=error_name,
                duration_ms=duration_ms,
            )

            # Playwright errors are generally retryable (timeout, crash, navigation)
            is_retryable = "timeout" in str(e).lower() or "navigation" in str(e).lower() or "crash" in str(e).lower()
            raise ScraperError(f"Playwright error for {url}: {e}", url=url, is_retryable=is_retryable)

        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass


def shutdown_browser() -> None:
    """Called during worker shutdown to clean up Chromium processes."""
    _cleanup_browser()
    logger.info("playwright_browser_shutdown")
