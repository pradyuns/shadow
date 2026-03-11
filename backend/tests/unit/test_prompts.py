"""Tests for Claude prompt templates."""

import pytest

from workers.classifier.prompts import (
    MAX_DIFF_CHARS,
    SYSTEM_PROMPT,
    build_user_prompt,
    truncate_diff,
)


class TestBuildUserPrompt:
    """Test user prompt construction."""

    def test_includes_competitor_name(self):
        prompt = build_user_prompt("Example Corp", "pricing", "https://example.com", "+test")
        assert "Example Corp" in prompt

    def test_includes_page_type(self):
        prompt = build_user_prompt("Test", "changelog", "https://example.com", "+test")
        assert "changelog" in prompt

    def test_includes_url(self):
        prompt = build_user_prompt("Test", "pricing", "https://example.com/pricing", "+test")
        assert "https://example.com/pricing" in prompt

    def test_includes_diff(self):
        prompt = build_user_prompt("Test", "pricing", "https://example.com", "+Price: $129")
        assert "+Price: $129" in prompt

    def test_none_competitor_shows_unknown(self):
        prompt = build_user_prompt(None, "pricing", "https://example.com", "+test")
        assert "Unknown" in prompt

    def test_truncated_adds_warning(self):
        prompt = build_user_prompt("Test", "pricing", "https://example.com", "+test", truncated=True)
        assert "truncated" in prompt.lower()

    def test_not_truncated_no_warning(self):
        prompt = build_user_prompt("Test", "pricing", "https://example.com", "+test", truncated=False)
        assert "truncated" not in prompt.lower()

    def test_diff_in_code_block(self):
        prompt = build_user_prompt("Test", "pricing", "https://example.com", "+test")
        assert "```diff" in prompt


class TestTruncateDiff:
    """Test diff truncation."""

    def test_short_diff_not_truncated(self):
        diff = "+Short change"
        result, was_truncated = truncate_diff(diff)
        assert result == diff
        assert was_truncated is False

    def test_long_diff_truncated(self):
        diff = "\n".join(f"+Line {i}" for i in range(10000))
        result, was_truncated = truncate_diff(diff)
        assert was_truncated is True
        assert len(result) <= MAX_DIFF_CHARS + 50  # +50 for truncation marker

    def test_truncated_diff_has_marker(self):
        diff = "x" * (MAX_DIFF_CHARS + 1000)
        result, was_truncated = truncate_diff(diff)
        assert "[... diff truncated ...]" in result

    def test_exact_length_not_truncated(self):
        diff = "x" * MAX_DIFF_CHARS
        result, was_truncated = truncate_diff(diff)
        assert was_truncated is False

    def test_custom_max_chars(self):
        diff = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        result, was_truncated = truncate_diff(diff, max_chars=10)
        assert was_truncated is True

    def test_empty_diff(self):
        result, was_truncated = truncate_diff("")
        assert result == ""
        assert was_truncated is False


class TestSystemPrompt:
    """Test system prompt content."""

    def test_contains_significance_levels(self):
        for level in ["critical", "high", "medium", "low", "noise"]:
            assert level in SYSTEM_PROMPT

    def test_contains_categories(self):
        for cat in [
            "pricing_change",
            "feature_launch",
            "feature_removal",
            "hiring_signal",
            "messaging_change",
            "partnership",
            "technical_change",
            "other",
        ]:
            assert cat in SYSTEM_PROMPT
