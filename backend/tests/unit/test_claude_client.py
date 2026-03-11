"""Tests for Claude API client with mocked Anthropic SDK."""

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from workers.classifier.schemas import ChangeCategory, ClassificationResult, SignificanceLevel


class TestClassifyChange:
    """Test the classify_change function with mocked Anthropic client."""

    def _make_mock_response(self, fixture_name):
        """Load a mock response fixture and create a mock Anthropic response."""
        fixture_path = os.path.join(
            os.path.dirname(__file__), "..", "fixtures", "mock_responses", f"{fixture_name}.json"
        )
        with open(fixture_path) as f:
            data = json.load(f)

        response = MagicMock()
        response.usage.input_tokens = data["usage"]["input_tokens"]
        response.usage.output_tokens = data["usage"]["output_tokens"]

        blocks = []
        for block_data in data["content"]:
            block = MagicMock()
            block.type = block_data["type"]
            if block_data["type"] == "tool_use":
                block.input = block_data["input"]
            blocks.append(block)

        response.content = blocks
        return response

    def test_successful_critical_classification(self):
        import anthropic as real_anthropic

        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 0
        cc._circuit_open_until = None

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response("claude_critical")

        with patch.object(real_anthropic, "Anthropic", return_value=mock_client):
            result = cc.classify_change(
                filtered_diff="+Price: $129/month\n-Price: $99/month",
                competitor_name="Example Corp",
                page_type="pricing",
                url="https://example.com/pricing",
            )

        assert result["error"] is None
        assert result["classification"]["significance_level"] == "critical"
        assert "pricing_change" in result["classification"]["categories"]
        assert result["prompt_tokens"] == 450
        assert result["completion_tokens"] == 120
        assert result["total_cost_usd"] > 0
        assert result["needs_review"] is False

    def test_successful_low_classification(self):
        import anthropic as real_anthropic

        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 0
        cc._circuit_open_until = None

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response("claude_low")

        with patch.object(real_anthropic, "Anthropic", return_value=mock_client):
            result = cc.classify_change(
                filtered_diff="+Minor copy change",
                competitor_name="Test",
                page_type="homepage",
                url="https://example.com",
            )

        assert result["classification"]["significance_level"] == "low"
        assert result["needs_review"] is False

    def test_cost_calculation(self):
        import anthropic as real_anthropic

        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 0
        cc._circuit_open_until = None

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response("claude_critical")

        with patch.object(real_anthropic, "Anthropic", return_value=mock_client):
            result = cc.classify_change(
                filtered_diff="+test",
                competitor_name="Test",
                page_type="pricing",
                url="https://example.com",
            )

        expected_cost = (450 * 3.0 / 1_000_000) + (120 * 15.0 / 1_000_000)
        assert result["total_cost_usd"] == round(expected_cost, 6)

    def test_auth_error_returns_error_result(self):
        import anthropic as real_anthropic

        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 0
        cc._circuit_open_until = None

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = real_anthropic.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )

        with patch.object(real_anthropic, "Anthropic", return_value=mock_client):
            result = cc.classify_change(
                filtered_diff="+test",
                competitor_name="Test",
                page_type="pricing",
                url="https://example.com",
            )

        assert result["error"] is not None
        assert "Authentication" in result["error"]
        assert result["needs_review"] is True
        assert result["total_cost_usd"] == 0.0

    def test_rate_limit_error_raises(self):
        import anthropic as real_anthropic

        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 0
        cc._circuit_open_until = None

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = real_anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429),
            body=None,
        )

        with patch.object(real_anthropic, "Anthropic", return_value=mock_client):
            with pytest.raises(real_anthropic.RateLimitError):
                cc.classify_change(
                    filtered_diff="+test",
                    competitor_name="Test",
                    page_type="pricing",
                    url="https://example.com",
                )

    def test_circuit_breaker_opens_after_threshold(self):
        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 0
        cc._circuit_open_until = None

        # Record non-retryable failures until threshold
        for _ in range(cc.CIRCUIT_BREAKER_THRESHOLD):
            cc._record_failure(is_retryable=False)

        assert cc._circuit_open_until is not None
        assert cc._check_circuit_breaker() is True

    def test_circuit_breaker_resets_on_success(self):
        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 3
        cc._circuit_open_until = None

        cc._record_success()
        assert cc._consecutive_failures == 0

    def test_circuit_breaker_cooldown_expires(self):
        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 5
        # Set cooldown to the past
        cc._circuit_open_until = datetime.now(timezone.utc) - timedelta(seconds=1)

        assert cc._check_circuit_breaker() is False
        assert cc._circuit_open_until is None

    def test_circuit_breaker_skips_classification(self):
        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 5
        cc._circuit_open_until = datetime.now(timezone.utc) + timedelta(minutes=5)

        result = cc.classify_change(
            filtered_diff="+test",
            competitor_name="Test",
            page_type="pricing",
            url="https://example.com",
        )

        assert result["needs_review"] is True
        assert "Circuit breaker" in result["error"]
        assert result["total_cost_usd"] == 0.0

        # Reset state
        cc._consecutive_failures = 0
        cc._circuit_open_until = None

    def test_retryable_failures_dont_trip_breaker(self):
        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 0
        cc._circuit_open_until = None

        for _ in range(10):
            cc._record_failure(is_retryable=True)

        assert cc._consecutive_failures == 0
        assert cc._circuit_open_until is None

    def test_no_tool_response_uses_fallback(self):
        import anthropic as real_anthropic

        import workers.classifier.claude_client as cc

        cc._consecutive_failures = 0
        cc._circuit_open_until = None

        mock_client = MagicMock()

        # Response with text block instead of tool_use
        response = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "This is a critical pricing change affecting enterprise customers."
        response.content = [text_block]
        mock_client.messages.create.return_value = response

        with patch.object(real_anthropic, "Anthropic", return_value=mock_client):
            result = cc.classify_change(
                filtered_diff="+test",
                competitor_name="Test",
                page_type="pricing",
                url="https://example.com",
            )

        assert result["needs_review"] is True
        assert result["classification"]["significance_level"] == "critical"


class TestDefaultClassification:
    """Test the default/fallback classification."""

    def test_default_classification_values(self):
        from workers.classifier.claude_client import _default_classification

        result = _default_classification()
        assert result["significance_level"] == "medium"
        assert "manual review" in result["summary"].lower()
        assert result["categories"] == ["other"]


class TestSafeParseToolResult:
    """Test best-effort parsing of malformed tool results."""

    def test_valid_result(self):
        from workers.classifier.claude_client import _safe_parse_tool_result

        result = _safe_parse_tool_result(
            {
                "significance_level": "high",
                "summary": "Test summary",
                "categories": ["pricing_change"],
            }
        )
        assert result["significance_level"] == "high"
        assert result["summary"] == "Test summary"

    def test_invalid_significance_defaults_to_medium(self):
        from workers.classifier.claude_client import _safe_parse_tool_result

        result = _safe_parse_tool_result(
            {
                "significance_level": "invalid",
                "summary": "Test",
                "categories": ["other"],
            }
        )
        assert result["significance_level"] == "medium"

    def test_invalid_categories_defaults_to_other(self):
        from workers.classifier.claude_client import _safe_parse_tool_result

        result = _safe_parse_tool_result(
            {
                "significance_level": "high",
                "summary": "Test",
                "categories": ["nonexistent_category"],
            }
        )
        assert result["categories"] == ["other"]

    def test_truncates_long_summary(self):
        from workers.classifier.claude_client import _safe_parse_tool_result

        result = _safe_parse_tool_result(
            {
                "significance_level": "high",
                "summary": "x" * 2000,
                "categories": ["other"],
            }
        )
        assert len(result["summary"]) == 1000

    def test_missing_fields_use_defaults(self):
        from workers.classifier.claude_client import _safe_parse_tool_result

        result = _safe_parse_tool_result({})
        assert result["significance_level"] == "medium"
        assert result["categories"] == ["other"]


class TestFallbackParse:
    """Test regex-based fallback parsing."""

    def test_extracts_significance_from_text(self):
        from workers.classifier.claude_client import _fallback_parse

        response = MagicMock()
        text_block = MagicMock()
        text_block.text = "This is a high significance change in pricing."
        response.content = [text_block]

        result = _fallback_parse(response)
        assert result["significance_level"] == "high"

    def test_extracts_categories_from_text(self):
        from workers.classifier.claude_client import _fallback_parse

        response = MagicMock()
        text_block = MagicMock()
        text_block.text = "This involves a pricing_change and a feature_launch."
        response.content = [text_block]

        result = _fallback_parse(response)
        assert "pricing_change" in result["categories"]
        assert "feature_launch" in result["categories"]

    def test_empty_response_returns_default(self):
        from workers.classifier.claude_client import _fallback_parse

        response = MagicMock()
        response.content = []

        result = _fallback_parse(response)
        assert result["significance_level"] == "medium"
        assert result["categories"] == ["other"]
