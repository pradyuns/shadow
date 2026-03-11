"""Tests for scraping tasks."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestInitiateScrapeCycle:
    @patch("app.db.postgres_sync.get_sync_db")
    @patch("redis.Redis.from_url")
    def test_dispatches_monitors(self, mock_from_url, mock_pg):
        from workers.tasks.scraping import initiate_scrape_cycle

        mock_redis = MagicMock()
        mock_from_url.return_value = mock_redis
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_redis.lock.return_value = mock_lock

        db = MagicMock()
        mock_pg.return_value = db
        result_mock = MagicMock()
        result_mock.all.return_value = [("id-1",), ("id-2",)]
        db.execute.return_value = result_mock

        result = initiate_scrape_cycle(batch_size=10)
        assert result["monitors_queued"] == 2
        assert result["batches"] >= 1
        mock_lock.release.assert_called_once()

    @patch("redis.Redis.from_url")
    def test_skips_when_lock_held(self, mock_from_url):
        from workers.tasks.scraping import initiate_scrape_cycle

        mock_redis = MagicMock()
        mock_from_url.return_value = mock_redis
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = False
        mock_redis.lock.return_value = mock_lock

        result = initiate_scrape_cycle()
        assert result["monitors_queued"] == 0
        assert result["skipped"] == "lock_held"

    @patch("app.db.postgres_sync.get_sync_db")
    @patch("redis.Redis.from_url")
    def test_no_monitors_due(self, mock_from_url, mock_pg):
        from workers.tasks.scraping import initiate_scrape_cycle

        mock_redis = MagicMock()
        mock_from_url.return_value = mock_redis
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_redis.lock.return_value = mock_lock

        db = MagicMock()
        mock_pg.return_value = db
        result_mock = MagicMock()
        result_mock.all.return_value = []
        db.execute.return_value = result_mock

        result = initiate_scrape_cycle()
        assert result["monitors_queued"] == 0
        assert result["batches"] == 0


class TestScrapeSingleUrl:
    @patch("workers.tasks.diffing.compute_diff")
    @patch("workers.scraper.text_extractor.extract_text")
    @patch("workers.scraper.factory.get_firecrawl_scraper")
    @patch("workers.scraper.factory.get_scraper")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_scrape_success(self, mock_pg, mock_mongo, mock_get_scraper, mock_get_firecrawl, mock_extract, mock_diff):
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
        monitor.url = "https://example.com"
        monitor.render_js = False
        monitor.use_firecrawl = False
        monitor.css_selector = None
        monitor.page_type = "pricing"
        monitor.check_interval_hours = 6
        monitor.consecutive_failures = 0
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        mock_get_firecrawl.return_value = None  # No Firecrawl configured

        scraper = MagicMock()
        mock_get_scraper.return_value = scraper
        scrape_result = MagicMock()
        scrape_result.raw_html = "<html>Hello</html>"
        scrape_result.http_status = 200
        scrape_result.render_method = "httpx"
        scrape_result.fetch_duration_ms = 100
        scraper.fetch.return_value = scrape_result

        mock_extract.return_value = {
            "extracted_text": "Hello",
            "text_hash": "abc123",
            "text_length": 5,
            "auto_upgrade_js": False,
        }

        mongo_db.snapshots.insert_one.return_value = MagicMock(inserted_id="snap-1")

        result = scrape_single_url("mon-1")
        assert result["status"] == "success"
        assert result["snapshot_id"] == "snap-1"
        mock_diff.delay.assert_called_once()

    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_scrape_monitor_not_found(self, mock_pg, mock_mongo):
        from workers.tasks.scraping import scrape_single_url

        db = MagicMock()
        mock_pg.return_value = db
        mock_mongo.return_value = MagicMock()

        db.execute.return_value.scalar_one_or_none.return_value = None

        result = scrape_single_url("mon-1")
        assert result["status"] == "not_found"

    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_scrape_inactive_monitor(self, mock_pg, mock_mongo):
        from workers.tasks.scraping import scrape_single_url

        db = MagicMock()
        mock_pg.return_value = db
        mock_mongo.return_value = MagicMock()

        monitor = MagicMock()
        monitor.is_active = False
        monitor.deleted_at = None
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        result = scrape_single_url("mon-1")
        assert result["status"] == "inactive"

    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_scrape_skips_recent(self, mock_pg, mock_mongo):
        from workers.tasks.scraping import scrape_single_url

        db = MagicMock()
        mock_pg.return_value = db
        mock_mongo.return_value = MagicMock()

        monitor = MagicMock()
        monitor.is_active = True
        monitor.deleted_at = None
        monitor.last_checked_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        result = scrape_single_url("mon-1")
        assert result["status"] == "skipped_recent"

    @patch("workers.scraper.factory.get_firecrawl_scraper")
    @patch("workers.scraper.factory.get_scraper")
    @patch("app.db.mongodb_sync.get_sync_mongo_db")
    @patch("app.db.postgres_sync.get_sync_db")
    def test_scrape_error_increments_failures(self, mock_pg, mock_mongo, mock_get_scraper, mock_get_firecrawl):
        from workers.scraper.base import ScraperError
        from workers.tasks.scraping import scrape_single_url

        db = MagicMock()
        mock_pg.return_value = db
        mock_mongo.return_value = MagicMock()

        monitor = MagicMock()
        monitor.is_active = True
        monitor.deleted_at = None
        monitor.last_checked_at = None
        monitor.render_js = False
        monitor.use_firecrawl = False
        monitor.url = "https://example.com"
        monitor.css_selector = None
        monitor.page_type = "pricing"
        monitor.check_interval_hours = 6
        monitor.consecutive_failures = 0
        db.execute.return_value.scalar_one_or_none.return_value = monitor

        mock_get_firecrawl.return_value = None  # No Firecrawl fallback

        scraper = MagicMock()
        mock_get_scraper.return_value = scraper
        scraper.fetch.side_effect = ScraperError("timeout", url="https://example.com", is_retryable=False)

        result = scrape_single_url("mon-1")
        assert result["status"] == "failed"
        assert monitor.consecutive_failures == 1
