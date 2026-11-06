from unittest.mock import MagicMock, patch

import pytest

from workers.scraper.base import ScraperError
from workers.scraper.playwright_scraper import PlaywrightScraper


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(
        "app.utils.validators.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )


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


def test_observed_private_request_is_aborted():
    browser = MagicMock()
    context = browser.new_context.return_value
    page = context.new_page.return_value
    page.goto.return_value.status = 200
    page.content.return_value = "ok"
    page.url = "https://example.com"
    with patch("workers.scraper.playwright_scraper._get_browser", return_value=browser):
        PlaywrightScraper().fetch("https://example.com")
    handler = context.route.call_args_list[-1].args[1]
    route = MagicMock()
    route.request.url = "http://127.0.0.1/admin"
    route.request.resource_type = "document"
    handler(route)
    route.abort.assert_called_once()
    route.continue_.assert_not_called()


def test_blocked_navigation_is_non_retryable():
    from workers.scraper.base import UnsafeDestinationError

    browser = MagicMock()
    context = browser.new_context.return_value
    page = context.new_page.return_value
    route = MagicMock()
    route.request.url = "http://127.0.0.1/secret"
    route.request.resource_type = "document"
    route.request.is_navigation_request.return_value = True

    def navigate(*args, **kwargs):
        context.route.call_args_list[-1].args[1](route)
        raise RuntimeError("navigation aborted")

    page.goto.side_effect = navigate
    with patch("workers.scraper.playwright_scraper._get_browser", return_value=browser):
        with pytest.raises(UnsafeDestinationError) as error:
            PlaywrightScraper().fetch("https://example.com")
    assert not error.value.is_retryable
    route.abort.assert_called_once()
