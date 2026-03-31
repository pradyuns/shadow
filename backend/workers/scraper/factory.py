"""Scraper factory — returns the right scraper based on monitor config.

Why a factory instead of inline if/else:
- Open/closed principle: add new scraper types without modifying task code
- Testability: easy to mock/swap scrapers in tests
- Encapsulates scraper lifecycle (e.g., httpx client pooling)
"""

from app.config import settings
from workers.scraper.base import BaseScraper
from workers.scraper.http_scraper import HttpScraper
from workers.scraper.playwright_scraper import PlaywrightScraper

# Module-level singleton for the HTTP scraper — shares connection pool across tasks.
# Playwright browser is already a singleton inside playwright_scraper.py.
_http_scraper: HttpScraper | None = None


def get_scraper(render_js: bool) -> BaseScraper:
    """Return the appropriate scraper for the given configuration.

    Args:
        render_js: If True, use Playwright for JS rendering.
                   If False, use lightweight httpx.

    Returns:
        A scraper instance ready to fetch URLs.
    """
    if render_js:
        return PlaywrightScraper()
    else:
        global _http_scraper
        if _http_scraper is None:
            _http_scraper = HttpScraper()
        return _http_scraper


def get_firecrawl_scraper():
    """Return a FirecrawlScraper if configured, otherwise None.

    Returns None (instead of raising) so callers can gracefully skip
    Firecrawl when no API key is set.
    """
    if not settings.firecrawl_api_key:
        return None

    from workers.scraper.firecrawl_scraper import FirecrawlScraper

    # Pass the resolved key explicitly so tests/config overrides on this module
    # don't depend on internals of firecrawl_scraper.settings.
    return FirecrawlScraper(api_key=settings.firecrawl_api_key)
