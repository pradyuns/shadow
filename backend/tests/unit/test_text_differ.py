"""Tests for text diffing module."""

import pytest

from workers.differ.text_differ import DiffResult, compute_text_diff


class TestComputeTextDiff:
    """Test unified diff computation."""

    def test_identical_texts_returns_empty(self):
        result = compute_text_diff("Hello World", "Hello World")
        assert result.is_identical is True
        assert result.unified_diff == ""
        assert result.lines_added == 0
        assert result.lines_removed == 0
        assert result.changed_hunks == 0
        assert result.diff_size_bytes == 0

    def test_added_line(self):
        before = "Line 1\nLine 2"
        after = "Line 1\nLine 2\nLine 3"
        result = compute_text_diff(before, after)
        assert result.is_identical is False
        assert result.lines_added >= 1
        assert "+Line 3" in result.unified_diff

    def test_removed_line(self):
        before = "Line 1\nLine 2\nLine 3"
        after = "Line 1\nLine 3"
        result = compute_text_diff(before, after)
        assert result.is_identical is False
        assert result.lines_removed >= 1
        assert "-Line 2" in result.unified_diff

    def test_modified_line(self):
        before = "Price: $99"
        after = "Price: $129"
        result = compute_text_diff(before, after)
        assert result.is_identical is False
        assert result.lines_added >= 1
        assert result.lines_removed >= 1
        assert "-Price: $99" in result.unified_diff
        assert "+Price: $129" in result.unified_diff

    def test_hunk_count(self):
        before = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8\nLine 9\nLine 10"
        after = "Line 1\nChanged 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8\nLine 9\nChanged 10"
        result = compute_text_diff(before, after, context_lines=1)
        assert result.changed_hunks >= 2

    def test_diff_size_bytes(self):
        before = "Hello"
        after = "World"
        result = compute_text_diff(before, after)
        assert result.diff_size_bytes == len(result.unified_diff.encode("utf-8"))

    def test_context_lines_parameter(self):
        before = "A\nB\nC\nD\nE"
        after = "A\nB\nX\nD\nE"
        result_small = compute_text_diff(before, after, context_lines=0)
        result_large = compute_text_diff(before, after, context_lines=5)
        assert len(result_large.unified_diff) >= len(result_small.unified_diff)

    def test_empty_strings(self):
        result = compute_text_diff("", "")
        assert result.is_identical is True

    def test_from_empty_to_content(self):
        result = compute_text_diff("", "New content here")
        assert result.is_identical is False
        assert result.lines_added >= 1

    def test_from_content_to_empty(self):
        result = compute_text_diff("Content here", "")
        assert result.is_identical is False
        assert result.lines_removed >= 1

    def test_large_diff(self):
        before = "\n".join(f"Line {i}" for i in range(1000))
        after = "\n".join(f"Modified {i}" for i in range(1000))
        result = compute_text_diff(before, after)
        assert result.is_identical is False
        assert result.lines_added == 1000
        assert result.lines_removed == 1000

    def test_unified_diff_format(self):
        before = "Old line"
        after = "New line"
        result = compute_text_diff(before, after)
        assert "---" in result.unified_diff
        assert "+++" in result.unified_diff
        assert "@@" in result.unified_diff

    def test_unicode_diff(self):
        before = "Prix: 29€/mois"
        after = "Prix: 39€/mois"
        result = compute_text_diff(before, after)
        assert result.is_identical is False
        assert "39€" in result.unified_diff
