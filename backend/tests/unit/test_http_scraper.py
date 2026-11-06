"""Tests for HTTP scraper."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from workers.scraper.base import ScraperError
from workers.scraper.http_scraper import HttpScraper, _get_user_agent


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(
        "app.utils.validators.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )


class TestHttpScraper:
    def test_fetch_success(self):
        scraper = HttpScraper()
        mock_response = MagicMock()
        mock_response.text = "<html><body>Hello</body></html>"
        mock_response.status_code = 200
        mock_response.url = "https://example.com"

        with patch.object(scraper._client, "get", return_value=mock_response):
            result = scraper.fetch("https://example.com")

        assert result.raw_html == "<html><body>Hello</body></html>"
        assert result.http_status == 200
        assert result.render_method == "httpx"
        assert result.fetch_duration_ms >= 0

    def test_fetch_timeout_raises_retryable(self):
        scraper = HttpScraper()

        with patch.object(scraper._client, "get", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(ScraperError) as exc_info:
                scraper.fetch("https://example.com")
            assert exc_info.value.is_retryable is True

    def test_fetch_connect_error_raises_retryable(self):
        scraper = HttpScraper()

        with patch.object(scraper._client, "get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ScraperError) as exc_info:
                scraper.fetch("https://example.com")
            assert exc_info.value.is_retryable is True

    def test_fetch_redirect_records_final_url(self):
        scraper = HttpScraper()
        mock_response = MagicMock()
        mock_response.text = "<html>Redirected</html>"
        mock_response.status_code = 200
        mock_response.url = "https://example.com/new-page"

        with patch.object(scraper._client, "get", return_value=mock_response):
            result = scraper.fetch("https://example.com/old-page")

        assert result.final_url == "https://example.com/new-page"

    def test_close(self):
        scraper = HttpScraper()
        with patch.object(scraper._client, "close") as mock_close:
            scraper.close()
            mock_close.assert_called_once()


class TestGetUserAgent:
    def test_rotates_user_agents(self):
        ua1 = _get_user_agent()
        ua2 = _get_user_agent()
        ua3 = _get_user_agent()
        # After 3 rotations, should cycle back
        assert isinstance(ua1, str)
        assert isinstance(ua2, str)
        assert len(ua1) > 10


def test_redirect_to_private_address_is_blocked_before_second_request():
    scraper = HttpScraper()
    redirect = httpx.Response(
        302, headers={"location": "http://127.0.0.1/admin"}, request=httpx.Request("GET", "https://example.com")
    )
    with patch.object(scraper._client, "get", return_value=redirect) as get:
        with pytest.raises(ScraperError, match="Unsafe scrape URL") as error:
            scraper.fetch("https://example.com")
    assert not error.value.is_retryable
    assert get.call_count == 1


def test_public_redirect_is_followed_manually():
    scraper = HttpScraper()
    first = httpx.Response(302, headers={"location": "/new"}, request=httpx.Request("GET", "https://example.com/old"))
    second = httpx.Response(200, text="ok", request=httpx.Request("GET", "https://example.com/new"))
    with patch.object(scraper._client, "get", side_effect=[first, second]) as get:
        result = scraper.fetch("https://example.com/old")
    assert get.call_count == 2
    assert result.final_url == "https://example.com/new"


def test_redirect_to_hostname_resolving_private_is_blocked(monkeypatch):
    def resolve(hostname, *args, **kwargs):
        ip = "10.0.0.2" if hostname == "internal.example" else "93.184.216.34"
        return [(2, 1, 6, "", (ip, 0))]

    monkeypatch.setattr("app.utils.validators.socket.getaddrinfo", resolve)
    scraper = HttpScraper()
    redirect = httpx.Response(
        302, headers={"location": "http://internal.example/"}, request=httpx.Request("GET", "https://example.com")
    )
    with patch.object(scraper._client, "get", return_value=redirect) as get:
        with pytest.raises(ScraperError, match="Unsafe scrape URL"):
            scraper.fetch("https://example.com")
    assert get.call_count == 1
