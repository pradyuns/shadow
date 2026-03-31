"""Tests for Firecrawl scraper and bot-detection fallback logic."""

from unittest.mock import MagicMock, patch

import pytest

from workers.scraper.base import ScraperError


def _mock_document(html="", markdown="", metadata=None):
    """Create a mock Firecrawl Document response object."""
    doc = MagicMock()
    doc.html = html
    doc.markdown = markdown
    doc.raw_html = html
    doc.metadata = metadata
    doc.links = []
    doc.images = []
    doc.screenshot = None
    doc.warning = None
    return doc


class TestFirecrawlScraper:
    """Tests for the FirecrawlScraper class."""

    @patch("workers.scraper.firecrawl_scraper.settings")
    def test_raises_if_no_api_key(self, mock_settings):
        mock_settings.firecrawl_api_key = ""
        from workers.scraper.firecrawl_scraper import FirecrawlScraper

        with pytest.raises(ScraperError) as exc_info:
            FirecrawlScraper()
        assert "not configured" in str(exc_info.value)
        assert exc_info.value.is_retryable is False

    @patch("firecrawl.FirecrawlApp")
    @patch("workers.scraper.firecrawl_scraper.settings")
    def test_fetch_success_html(self, mock_settings, mock_firecrawl_cls):
        mock_settings.firecrawl_api_key = "fc-test-key"
        from workers.scraper.firecrawl_scraper import FirecrawlScraper

        mock_client = MagicMock()
        mock_firecrawl_cls.return_value = mock_client
        mock_client.scrape.return_value = _mock_document(html="<html><body>Real content</body></html>")

        scraper = FirecrawlScraper(api_key="fc-test-key")
        result = scraper.fetch("https://example.com")

        assert result.raw_html == "<html><body>Real content</body></html>"
        assert result.http_status == 200
        assert result.render_method == "firecrawl"
        assert result.fetch_duration_ms >= 0
        mock_client.scrape.assert_called_once()
        # Verify SDK params are passed correctly
        call_kwargs = mock_client.scrape.call_args
        assert call_kwargs.kwargs["formats"] == ["html"]
        assert call_kwargs.kwargs["only_main_content"] is True
        assert call_kwargs.kwargs["block_ads"] is True
        assert call_kwargs.kwargs["timeout"] == 30000  # 30s * 1000

    @patch("firecrawl.FirecrawlApp")
    @patch("workers.scraper.firecrawl_scraper.settings")
    def test_fetch_fallback_to_markdown(self, mock_settings, mock_firecrawl_cls):
        mock_settings.firecrawl_api_key = "fc-test-key"
        from workers.scraper.firecrawl_scraper import FirecrawlScraper

        mock_client = MagicMock()
        mock_firecrawl_cls.return_value = mock_client
        # No HTML returned, but markdown is available
        mock_client.scrape.return_value = _mock_document(html="", markdown="# Hello World\nSome content")

        scraper = FirecrawlScraper(api_key="fc-test-key")
        result = scraper.fetch("https://example.com")

        assert "<pre>" in result.raw_html
        assert "Hello World" in result.raw_html
        assert result.render_method == "firecrawl"

    @patch("firecrawl.FirecrawlApp")
    @patch("workers.scraper.firecrawl_scraper.settings")
    def test_fetch_extracts_http_status_from_metadata(self, mock_settings, mock_firecrawl_cls):
        """Test that the real HTTP status code is extracted from Document metadata."""
        mock_settings.firecrawl_api_key = "fc-test-key"
        from workers.scraper.firecrawl_scraper import FirecrawlScraper

        mock_client = MagicMock()
        mock_firecrawl_cls.return_value = mock_client
        metadata = MagicMock()
        metadata.model_dump.return_value = {"statusCode": 403, "title": "Forbidden"}
        mock_client.scrape.return_value = _mock_document(
            html="<html>Forbidden</html>",
            metadata=metadata,
        )

        scraper = FirecrawlScraper(api_key="fc-test-key")
        result = scraper.fetch("https://example.com")

        assert result.http_status == 403

    @patch("firecrawl.FirecrawlApp")
    @patch("workers.scraper.firecrawl_scraper.settings")
    def test_fetch_passes_css_selector_as_include_tags(self, mock_settings, mock_firecrawl_cls):
        """Test that css_selector is forwarded to Firecrawl as include_tags."""
        mock_settings.firecrawl_api_key = "fc-test-key"
        from workers.scraper.firecrawl_scraper import FirecrawlScraper

        mock_client = MagicMock()
        mock_firecrawl_cls.return_value = mock_client
        mock_client.scrape.return_value = _mock_document(html="<div>content</div>")

        scraper = FirecrawlScraper(api_key="fc-test-key")
        scraper.fetch("https://example.com", css_selector=".main-content")

        call_kwargs = mock_client.scrape.call_args.kwargs
        assert call_kwargs["include_tags"] == [".main-content"]

    @patch("firecrawl.FirecrawlApp")
    @patch("workers.scraper.firecrawl_scraper.settings")
    def test_fetch_no_include_tags_without_css_selector(self, mock_settings, mock_firecrawl_cls):
        """Test that include_tags is not passed when no css_selector is given."""
        mock_settings.firecrawl_api_key = "fc-test-key"
        from workers.scraper.firecrawl_scraper import FirecrawlScraper

        mock_client = MagicMock()
        mock_firecrawl_cls.return_value = mock_client
        mock_client.scrape.return_value = _mock_document(html="<div>content</div>")

        scraper = FirecrawlScraper(api_key="fc-test-key")
        scraper.fetch("https://example.com")

        call_kwargs = mock_client.scrape.call_args.kwargs
        assert "include_tags" not in call_kwargs

    @patch("firecrawl.FirecrawlApp")
    @patch("workers.scraper.firecrawl_scraper.settings")
    def test_fetch_api_error(self, mock_settings, mock_firecrawl_cls):
        mock_settings.firecrawl_api_key = "fc-test-key"
        from workers.scraper.firecrawl_scraper import FirecrawlScraper

        mock_client = MagicMock()
        mock_firecrawl_cls.return_value = mock_client
        mock_client.scrape.side_effect = Exception("Firecrawl API error: 500")

        scraper = FirecrawlScraper(api_key="fc-test-key")
        with pytest.raises(ScraperError) as exc_info:
            scraper.fetch("https://example.com")
        assert exc_info.value.is_retryable is False

    @patch("firecrawl.FirecrawlApp")
    @patch("workers.scraper.firecrawl_scraper.settings")
    def test_fetch_rate_limit_is_retryable(self, mock_settings, mock_firecrawl_cls):
        mock_settings.firecrawl_api_key = "fc-test-key"
        from workers.scraper.firecrawl_scraper import FirecrawlScraper

        mock_client = MagicMock()
        mock_firecrawl_cls.return_value = mock_client
        mock_client.scrape.side_effect = Exception("429 Rate limit exceeded")

        scraper = FirecrawlScraper(api_key="fc-test-key")
        with pytest.raises(ScraperError) as exc_info:
            scraper.fetch("https://example.com")
        assert exc_info.value.is_retryable is True

    @patch("firecrawl.FirecrawlApp")
    @patch("workers.scraper.firecrawl_scraper.settings")
    def test_fetch_payment_error(self, mock_settings, mock_firecrawl_cls):
        """Test that 402 payment errors are detected and logged."""
        mock_settings.firecrawl_api_key = "fc-test-key"
        from workers.scraper.firecrawl_scraper import FirecrawlScraper

        mock_client = MagicMock()
        mock_firecrawl_cls.return_value = mock_client
        mock_client.scrape.side_effect = Exception("402 Payment required")

        scraper = FirecrawlScraper(api_key="fc-test-key")
        with pytest.raises(ScraperError) as exc_info:
            scraper.fetch("https://example.com")
        # Payment errors are not retryable
        assert exc_info.value.is_retryable is False

    @patch("firecrawl.FirecrawlApp")
    @patch("workers.scraper.firecrawl_scraper.settings")
    def test_fetch_custom_timeout(self, mock_settings, mock_firecrawl_cls):
        """Test that custom timeout is converted to milliseconds correctly."""
        mock_settings.firecrawl_api_key = "fc-test-key"
        from workers.scraper.firecrawl_scraper import FirecrawlScraper

        mock_client = MagicMock()
        mock_firecrawl_cls.return_value = mock_client
        mock_client.scrape.return_value = _mock_document(html="<html>ok</html>")

        scraper = FirecrawlScraper(api_key="fc-test-key")
        scraper.fetch("https://example.com", timeout_seconds=60)

        call_kwargs = mock_client.scrape.call_args.kwargs
        assert call_kwargs["timeout"] == 60000


class TestFirecrawlFactory:
    """Tests for get_firecrawl_scraper factory function."""

    @patch("workers.scraper.factory.settings")
    def test_returns_none_when_no_key(self, mock_settings):
        mock_settings.firecrawl_api_key = ""
        from workers.scraper.factory import get_firecrawl_scraper

        assert get_firecrawl_scraper() is None

    @patch("firecrawl.FirecrawlApp")
    @patch("workers.scraper.factory.settings")
    def test_returns_scraper_when_configured(self, mock_settings, mock_firecrawl_cls):
        mock_settings.firecrawl_api_key = "fc-test-key"
        from workers.scraper.factory import get_firecrawl_scraper

        scraper = get_firecrawl_scraper()
        assert scraper is not None


class TestBotDetection:
    """Tests for the _looks_like_bot_detection helper."""

    def test_detects_captcha_page(self):
        from workers.tasks.scraping import _looks_like_bot_detection

        assert _looks_like_bot_detection("Robot or human?") is True
        assert _looks_like_bot_detection("Please complete the CAPTCHA") is True
        assert _looks_like_bot_detection("Access Denied") is True
        assert _looks_like_bot_detection("Checking your browser before accessing") is True
        assert _looks_like_bot_detection("Attention Required! | Cloudflare") is True

    def test_ignores_long_text(self):
        from workers.tasks.scraping import _looks_like_bot_detection

        # Long text with bot keyword should NOT trigger (real pages mention "robot" sometimes)
        long_text = "This is a real page about robots. " * 20
        assert _looks_like_bot_detection(long_text) is False

    def test_ignores_normal_short_text(self):
        from workers.tasks.scraping import _looks_like_bot_detection

        assert _looks_like_bot_detection("Hello World") is False
        assert _looks_like_bot_detection("Pricing: $29/month") is False
        assert _looks_like_bot_detection("") is False


class TestScrapeSingleUrlFirecrawlFallback:
    """Tests for Firecrawl fallback in scrape_single_url."""

    @patch("workers.tasks.diffing.compute_diff")
    @patch("workers.scraper.text_extractor.extract_text")
    @patch("workers.scraper.factory.get_firecrawl_scraper")
    @patch("workers.scraper.factory.get_scraper")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_bot_detection_triggers_firecrawl_fallback(
        self, mock_pg, mock_mongo, mock_get_scraper, mock_get_firecrawl, mock_extract, mock_diff
    ):
        from workers.tasks.scraping import scrape_single_url

        db = MagicMock()
        mock_pg.return_value = db
        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        monitor = MagicMock()
        monitor.id = "mon-1"
        monitor.is_active = True
        monitor.deleted_at = None
        monitor.last_checked_at = None
        monitor.url = "https://www.walmart.com/browse/electronics"
        monitor.render_js = False
        monitor.use_firecrawl = False
        monitor.css_selector = None
        monitor.page_type = "pricing"
        monitor.check_interval_hours = 6
        monitor.consecutive_failures = 0
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        # Primary scraper returns bot-detection page
        primary_scraper = MagicMock()
        mock_get_scraper.return_value = primary_scraper
        primary_result = MagicMock()
        primary_result.raw_html = "<html><body>Robot or human?</body></html>"
        primary_result.http_status = 200
        primary_result.render_method = "httpx"
        primary_result.fetch_duration_ms = 100
        primary_scraper.fetch.return_value = primary_result

        # Firecrawl scraper returns real content
        firecrawl_scraper = MagicMock()
        mock_get_firecrawl.return_value = firecrawl_scraper
        firecrawl_result = MagicMock()
        firecrawl_result.raw_html = "<html><body><h1>Electronics</h1><p>Real content</p></body></html>"
        firecrawl_result.http_status = 200
        firecrawl_result.render_method = "firecrawl"
        firecrawl_result.fetch_duration_ms = 2000
        firecrawl_scraper.fetch.return_value = firecrawl_result

        # First call returns bot-detection text, second call returns real content
        mock_extract.side_effect = [
            {
                "extracted_text": "Robot or human?",
                "text_hash": "bot-hash",
                "text_length": 15,
                "auto_upgrade_js": False,
            },
            {
                "extracted_text": "Electronics Real content here with lots of products",
                "text_hash": "real-hash",
                "text_length": 51,
                "auto_upgrade_js": False,
            },
        ]

        mongo_db.snapshots.insert_one.return_value = MagicMock(inserted_id="snap-1")

        result = scrape_single_url("mon-1")
        assert result["status"] == "success"
        assert result["render_method"] == "firecrawl"
        firecrawl_scraper.fetch.assert_called_once()

    @patch("workers.tasks.diffing.compute_diff")
    @patch("workers.scraper.text_extractor.extract_text")
    @patch("workers.scraper.factory.get_firecrawl_scraper")
    @patch("workers.scraper.factory.get_scraper")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_use_firecrawl_flag_skips_primary(
        self, mock_pg, mock_mongo, mock_get_scraper, mock_get_firecrawl, mock_extract, mock_diff
    ):
        from workers.tasks.scraping import scrape_single_url

        db = MagicMock()
        mock_pg.return_value = db
        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        monitor = MagicMock()
        monitor.id = "mon-2"
        monitor.is_active = True
        monitor.deleted_at = None
        monitor.last_checked_at = None
        monitor.url = "https://www.walmart.com"
        monitor.render_js = False
        monitor.use_firecrawl = True
        monitor.css_selector = None
        monitor.page_type = "pricing"
        monitor.check_interval_hours = 6
        monitor.consecutive_failures = 0
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        # Firecrawl returns content directly
        firecrawl_scraper = MagicMock()
        mock_get_firecrawl.return_value = firecrawl_scraper
        firecrawl_result = MagicMock()
        firecrawl_result.raw_html = "<html>Walmart Content</html>"
        firecrawl_result.http_status = 200
        firecrawl_result.render_method = "firecrawl"
        firecrawl_result.fetch_duration_ms = 1500
        firecrawl_scraper.fetch.return_value = firecrawl_result

        mock_extract.return_value = {
            "extracted_text": "Walmart Content",
            "text_hash": "walmart-hash",
            "text_length": 15,
            "auto_upgrade_js": False,
        }

        mongo_db.snapshots.insert_one.return_value = MagicMock(inserted_id="snap-2")

        result = scrape_single_url("mon-2")
        assert result["status"] == "success"
        assert result["render_method"] == "firecrawl"
        # Primary scraper should NOT have been called
        mock_get_scraper.assert_not_called()

    @patch("workers.tasks.diffing.compute_diff")
    @patch("workers.scraper.text_extractor.extract_text")
    @patch("workers.scraper.factory.get_firecrawl_scraper")
    @patch("workers.scraper.factory.get_scraper")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_no_firecrawl_when_not_configured(
        self, mock_pg, mock_mongo, mock_get_scraper, mock_get_firecrawl, mock_extract, mock_diff
    ):
        """When Firecrawl is not configured, bot-detected content is stored as-is."""
        from workers.tasks.scraping import scrape_single_url

        db = MagicMock()
        mock_pg.return_value = db
        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        monitor = MagicMock()
        monitor.id = "mon-3"
        monitor.is_active = True
        monitor.deleted_at = None
        monitor.last_checked_at = None
        monitor.url = "https://example.com"
        monitor.render_js = False
        monitor.use_firecrawl = False
        monitor.css_selector = None
        monitor.page_type = "pricing"
        monitor.check_interval_hours = 6
        monitor.consecutive_failures = 0
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        primary_scraper = MagicMock()
        mock_get_scraper.return_value = primary_scraper
        primary_result = MagicMock()
        primary_result.raw_html = "<html>Robot or human?</html>"
        primary_result.http_status = 200
        primary_result.render_method = "httpx"
        primary_result.fetch_duration_ms = 100
        primary_scraper.fetch.return_value = primary_result

        # No Firecrawl configured
        mock_get_firecrawl.return_value = None

        mock_extract.return_value = {
            "extracted_text": "Robot or human?",
            "text_hash": "bot-hash",
            "text_length": 15,
            "auto_upgrade_js": False,
        }

        mongo_db.snapshots.insert_one.return_value = MagicMock(inserted_id="snap-3")

        result = scrape_single_url("mon-3")
        assert result["status"] == "success"
        # Bot content was stored since no fallback available
        assert result["text_hash"] == "bot-hash"

    @patch("workers.scraper.factory.get_firecrawl_scraper")
    @patch("workers.scraper.factory.get_scraper")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_primary_error_fallback_to_firecrawl(self, mock_pg, mock_mongo, mock_get_scraper, mock_get_firecrawl):
        """When primary scraper raises ScraperError, Firecrawl is tried as fallback."""
        from workers.tasks.scraping import scrape_single_url

        db = MagicMock()
        mock_pg.return_value = db
        mongo_db = MagicMock()
        mock_mongo.return_value = mongo_db

        monitor = MagicMock()
        monitor.id = "mon-4"
        monitor.is_active = True
        monitor.deleted_at = None
        monitor.last_checked_at = None
        monitor.url = "https://example.com"
        monitor.render_js = False
        monitor.use_firecrawl = False
        monitor.css_selector = None
        monitor.page_type = "pricing"
        monitor.check_interval_hours = 6
        monitor.consecutive_failures = 0
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        # Primary scraper fails
        primary_scraper = MagicMock()
        mock_get_scraper.return_value = primary_scraper
        primary_scraper.fetch.side_effect = ScraperError("Connection refused", url="https://example.com")

        # Firecrawl succeeds
        firecrawl_scraper = MagicMock()
        mock_get_firecrawl.return_value = firecrawl_scraper
        firecrawl_result = MagicMock()
        firecrawl_result.raw_html = "<html>Real content</html>"
        firecrawl_result.http_status = 200
        firecrawl_result.render_method = "firecrawl"
        firecrawl_result.fetch_duration_ms = 1000
        firecrawl_scraper.fetch.return_value = firecrawl_result

        with (
            patch("workers.scraper.text_extractor.extract_text") as mock_extract,
            patch("workers.tasks.diffing.compute_diff"),
        ):
            mock_extract.return_value = {
                "extracted_text": "Real content",
                "text_hash": "real-hash",
                "text_length": 12,
                "auto_upgrade_js": False,
            }
            mongo_db.snapshots.insert_one.return_value = MagicMock(inserted_id="snap-4")

            result = scrape_single_url("mon-4")
            assert result["status"] == "success"
            assert result["render_method"] == "firecrawl"
