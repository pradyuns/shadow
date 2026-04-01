from unittest.mock import MagicMock, patch

import pytest

from workers.scraper.base import ScraperError
from workers.scraper.playwright_scraper import PlaywrightScraper


def test_fetch_closes_page_and_context_on_success():
    scraper = PlaywrightScraper()
    browser = MagicMock()
    context = MagicMock()
    page = MagicMock()
    response = MagicMock()
    response.status = 200

    browser.new_context.return_value = context
    context.new_page.return_value = page
    page.goto.return_value = response
    page.content.return_value = "<html><body>ok</body></html>"
    page.url = "https://example.com"

    with patch("workers.scraper.playwright_scraper._get_browser", return_value=browser):
        result = scraper.fetch("https://example.com")

    assert result.http_status == 200
    page.close.assert_called_once()
    context.close.assert_called_once()


def test_fetch_closes_context_when_page_creation_fails():
    scraper = PlaywrightScraper()
    browser = MagicMock()
    context = MagicMock()

    browser.new_context.return_value = context
    context.new_page.side_effect = Exception("new page failed")

    with (
        patch("workers.scraper.playwright_scraper._get_browser", return_value=browser),
        pytest.raises(ScraperError),
    ):
        scraper.fetch("https://example.com")

    context.close.assert_called_once()
