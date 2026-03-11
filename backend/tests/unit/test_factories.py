"""Tests for scraper and notifier factories."""

import pytest

from workers.notifier.email_notifier import EmailNotifier
from workers.notifier.factory import get_notifier
from workers.notifier.slack_notifier import SlackNotifier
from workers.scraper.factory import get_scraper
from workers.scraper.http_scraper import HttpScraper


class TestNotifierFactory:
    def test_get_slack_notifier(self):
        notifier = get_notifier("slack")
        assert isinstance(notifier, SlackNotifier)

    def test_get_email_notifier(self):
        notifier = get_notifier("email")
        assert isinstance(notifier, EmailNotifier)

    def test_get_invalid_channel_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            get_notifier("discord")

    def test_slack_singleton(self):
        n1 = get_notifier("slack")
        n2 = get_notifier("slack")
        assert n1 is n2


class TestScraperFactory:
    def test_get_http_scraper(self):
        scraper = get_scraper(render_js=False)
        assert isinstance(scraper, HttpScraper)

    def test_http_scraper_singleton(self):
        s1 = get_scraper(render_js=False)
        s2 = get_scraper(render_js=False)
        assert s1 is s2
