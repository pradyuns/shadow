"""Tests for HTML text extraction."""

import hashlib

import pytest

from workers.scraper.text_extractor import REMOVE_TAGS, extract_text


class TestExtractText:
    """Test text extraction from HTML."""

    def test_basic_extraction(self):
        html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
        result = extract_text(html)
        assert "Hello" in result["extracted_text"]
        assert "World" in result["extracted_text"]

    def test_strips_script_tags(self):
        html = '<html><body><script>alert("xss")</script><p>Content</p></body></html>'
        result = extract_text(html)
        assert "alert" not in result["extracted_text"]
        assert "Content" in result["extracted_text"]

    def test_strips_style_tags(self):
        html = "<html><body><style>body{color:red}</style><p>Visible</p></body></html>"
        result = extract_text(html)
        assert "color" not in result["extracted_text"]
        assert "Visible" in result["extracted_text"]

    def test_strips_all_remove_tags(self):
        for tag in REMOVE_TAGS:
            html = f"<html><body><{tag}>hidden</{tag}><p>Visible</p></body></html>"
            result = extract_text(html)
            assert "Visible" in result["extracted_text"]

    def test_css_selector_extraction(self):
        html = '<html><body><div class="main">Target</div><div class="sidebar">Other</div></body></html>'
        result = extract_text(html, css_selector=".main")
        assert "Target" in result["extracted_text"]
        # Sidebar content should not be included when selector matches
        assert "Other" not in result["extracted_text"]

    def test_css_selector_no_match_returns_full_text(self):
        html = "<html><body><p>Full page content</p></body></html>"
        result = extract_text(html, css_selector=".nonexistent")
        # When selector doesn't match, falls back to full page
        assert "Full page content" in result["extracted_text"]

    def test_text_hash_consistency(self):
        html = "<html><body><p>Consistent content</p></body></html>"
        result1 = extract_text(html)
        result2 = extract_text(html)
        assert result1["text_hash"] == result2["text_hash"]

    def test_text_hash_is_sha256(self):
        html = "<html><body><p>Test</p></body></html>"
        result = extract_text(html)
        assert len(result["text_hash"]) == 64  # SHA-256 hex length

    def test_text_hash_changes_with_content(self):
        result1 = extract_text("<html><body><p>Version 1</p></body></html>")
        result2 = extract_text("<html><body><p>Version 2</p></body></html>")
        assert result1["text_hash"] != result2["text_hash"]

    def test_text_length_accurate(self):
        html = "<html><body><p>Hello World</p></body></html>"
        result = extract_text(html)
        assert result["text_length"] == len(result["extracted_text"])

    def test_malformed_html_handled(self):
        html = "<html><body><p>Unclosed <b>tag<div>Nested"
        result = extract_text(html)
        assert "Unclosed" in result["extracted_text"]
        assert "Nested" in result["extracted_text"]

    def test_whitespace_normalization(self):
        html = "<html><body><p>Line 1</p>\n\n\n\n\n<p>Line 2</p></body></html>"
        result = extract_text(html)
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in result["extracted_text"]

    def test_unicode_content(self):
        html = "<html><body><p>Prix: 29€/mois</p><p>日本語テスト</p></body></html>"
        result = extract_text(html)
        assert "29€" in result["extracted_text"]
        assert "日本語テスト" in result["extracted_text"]

    def test_empty_html(self):
        result = extract_text("")
        assert result["text_length"] == 0
        assert result["extracted_text"] == ""

    def test_js_detection_triggers(self):
        html = """<html><body>
        <noscript>Enable JS</noscript>
        <div id="root"></div>
        </body></html>"""
        result = extract_text(html)
        assert result["auto_upgrade_js"] is True

    def test_js_detection_not_triggered_for_normal_page(self):
        html = "<html><body><h1>Pricing</h1><p>Lots of content here that is meaningful and long enough to pass the threshold for JS detection.</p></body></html>"
        result = extract_text(html)
        assert result["auto_upgrade_js"] is False

    def test_real_page_fixture(self):
        """Test with sample HTML fixture."""
        import os

        fixture_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample_html", "page_v1.html")
        with open(fixture_path) as f:
            html = f.read()
        result = extract_text(html)
        assert "Pricing" in result["extracted_text"]
        assert "$99/month" in result["extracted_text"]
        # Script content should be stripped
        assert "tracking" not in result["extracted_text"]
