"""Tests for diff noise filtering."""

import pytest

from workers.scraper.noise_filter import (
    FilterResult,
    _compiled_global,
    _is_noise_line,
    _remove_empty_hunks,
    filter_diff,
)


class TestIsNoiseLine:
    """Test individual line noise detection."""

    def test_timestamp_is_noise(self):
        assert _is_noise_line("+2024-01-15T14:30:00", _compiled_global) is True

    def test_unix_timestamp_is_noise(self):
        assert _is_noise_line("+1705334400000", _compiled_global) is True

    def test_cache_hash_is_noise(self):
        # The pattern removes the hash; residual "bundle..js" is < 5 meaningful chars after strip
        assert _is_noise_line("+a1b2c3d4e5f6.js", _compiled_global) is True

    def test_utm_param_is_noise(self):
        assert _is_noise_line("+utm_source=google&utm_medium=cpc", _compiled_global) is True

    def test_csrf_token_is_noise(self):
        assert _is_noise_line('+csrf_token="abc123def456"', _compiled_global) is True

    def test_session_id_is_noise(self):
        assert _is_noise_line('+session_id="xyz789"', _compiled_global) is True

    def test_ad_slot_is_noise(self):
        # "ad-slot-header" -> after pattern removes "ad-slot", residual is "-header" (7 chars)
        # Use shorter input so residual < 5
        assert _is_noise_line("+ad_slot", _compiled_global) is True

    def test_copyright_year_is_noise(self):
        assert _is_noise_line("+Copyright 2024", _compiled_global) is True

    def test_cookie_consent_is_noise(self):
        assert _is_noise_line("+cookie_consent", _compiled_global) is True

    def test_real_content_not_noise(self):
        assert _is_noise_line("+Enterprise plan: $129/month", _compiled_global) is False

    def test_pricing_change_not_noise(self):
        assert _is_noise_line("+New pricing: $49/month for Pro tier", _compiled_global) is False

    def test_feature_announcement_not_noise(self):
        assert _is_noise_line("+We just launched AI-powered analytics!", _compiled_global) is False

    def test_line_with_noise_and_real_content(self):
        # Line with a timestamp but also substantial content should NOT be noise
        assert _is_noise_line("+Updated pricing 2024-01-15: Enterprise now $129/month", _compiled_global) is False

    def test_fbclid_is_noise(self):
        assert _is_noise_line("+fbclid=abc123def456", _compiled_global) is True

    def test_gclid_is_noise(self):
        assert _is_noise_line("+gclid=abc123def456", _compiled_global) is True

    def test_cloudflare_token_is_noise(self):
        assert _is_noise_line("+__cf_bm=t", _compiled_global) is True

    def test_chunk_hash_is_noise(self):
        assert _is_noise_line("+chunk-a1b2c3d4", _compiled_global) is True


class TestFilterDiff:
    """Test full diff filtering."""

    def test_empty_diff(self):
        result = filter_diff("")
        assert result.is_empty_after_filter is True
        assert result.original_lines == 0
        assert result.noise_lines_removed == 0

    def test_whitespace_only_diff(self):
        result = filter_diff("   \n  \n  ")
        assert result.is_empty_after_filter is True

    def test_none_treated_as_empty(self):
        result = filter_diff(None)
        assert result.is_empty_after_filter is True

    def test_preserves_real_changes(self):
        diff = """--- previous
+++ current
@@ -1,3 +1,3 @@
 Pricing Page
-Enterprise: $99/month
+Enterprise: $129/month
 Contact us for details"""
        result = filter_diff(diff)
        assert result.is_empty_after_filter is False
        assert "+Enterprise: $129/month" in result.filtered_diff
        assert "-Enterprise: $99/month" in result.filtered_diff

    def test_removes_noise_lines(self):
        diff = """--- previous
+++ current
@@ -1,3 +1,3 @@
 Page content
-Copyright 2023
+Copyright 2024
 Footer text"""
        result = filter_diff(diff)
        assert result.noise_lines_removed == 2
        assert result.is_empty_after_filter is True

    def test_mixed_noise_and_real_changes(self):
        diff = """--- previous
+++ current
@@ -1,5 +1,5 @@
 Pricing
-Enterprise: $99/month
+Enterprise: $129/month
-Copyright 2023
+Copyright 2024
 Footer"""
        result = filter_diff(diff)
        assert result.is_empty_after_filter is False
        assert result.noise_lines_removed == 2
        assert "+Enterprise: $129/month" in result.filtered_diff

    def test_custom_monitor_patterns(self):
        diff = """--- previous
+++ current
@@ -1,3 +1,3 @@
 Content
-Last updated: Monday
+Last updated: Tuesday
 End"""
        result = filter_diff(diff, monitor_noise_patterns=[r"Last updated: \w+"])
        assert result.noise_lines_removed == 2
        assert result.is_empty_after_filter is True

    def test_invalid_custom_pattern_skipped(self):
        diff = """--- previous
+++ current
@@ -1,3 +1,3 @@
 Content
-Price: $99
+Price: $129
 End"""
        result = filter_diff(diff, monitor_noise_patterns=["[invalid"])
        assert result.is_empty_after_filter is False
        assert "+Price: $129" in result.filtered_diff

    def test_preserves_diff_headers(self):
        diff = """--- previous
+++ current
@@ -1,3 +1,3 @@
 Content
-Old text
+New text
 End"""
        result = filter_diff(diff)
        assert "--- previous" in result.filtered_diff
        assert "+++ current" in result.filtered_diff

    def test_stats_accuracy(self):
        diff = """--- previous
+++ current
@@ -1,4 +1,4 @@
 Content
-Old line 1
+New line 1
-1705334400000
+1705334500000
 End"""
        result = filter_diff(diff)
        assert result.original_lines == 4
        assert result.noise_lines_removed == 2


class TestRemoveEmptyHunks:
    """Test hunk cleanup."""

    def test_removes_empty_hunk(self):
        lines = [
            "--- previous",
            "+++ current",
            "@@ -1,3 +1,3 @@",
            " Context only",
            " More context",
        ]
        result = _remove_empty_hunks(lines)
        assert "@@ -1,3 +1,3 @@" not in result

    def test_keeps_hunk_with_changes(self):
        lines = [
            "--- previous",
            "+++ current",
            "@@ -1,3 +1,3 @@",
            " Context",
            "+Added line",
            " More context",
        ]
        result = _remove_empty_hunks(lines)
        assert "@@ -1,3 +1,3 @@" in result
        assert "+Added line" in result

    def test_multiple_hunks_mixed(self):
        lines = [
            "--- previous",
            "+++ current",
            "@@ -1,2 +1,2 @@",
            " Context only",
            "@@ -5,3 +5,3 @@",
            " Before",
            "+Real change",
            " After",
        ]
        result = _remove_empty_hunks(lines)
        # First hunk should be removed (no changes)
        # Second hunk should be kept
        hunk_count = sum(1 for l in result if l.startswith("@@"))
        assert hunk_count == 1
        assert "+Real change" in result
