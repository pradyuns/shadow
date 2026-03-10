"""Claude API client for change classification.

Design decisions:

1. Anthropic SDK tool_use for structured output:
   Instead of asking Claude to output JSON in a text response (fragile),
   we use the SDK's tool_use feature which constrains Claude to respond
   with a JSON object matching our Pydantic schema. This eliminates 95%+
   of parsing failures.

2. Circuit breaker pattern:
   If Claude API has persistent failures (auth errors, model down), we
   stop wasting retries and queue diffs for manual review. The breaker
   trips after 5 consecutive non-retryable failures and resets after
   5 minutes. This prevents a cascade of failed tasks from flooding
   the Celery queue with retries.

3. Fallback parsing:
   Even with structured output, edge cases exist (model updates, SDK bugs).
   If structured output fails, we attempt regex-based extraction from the
   raw text response as a last resort.

4. Cost tracking:
   Every API call records token usage and estimated cost. This enables
   budget monitoring and spend alerts.
"""

import json
import re
import time
from datetime import datetime, timezone

import structlog

from app.config import settings
from workers.classifier.prompts import SYSTEM_PROMPT, build_user_prompt, truncate_diff
from workers.classifier.schemas import (
    ChangeCategory,
    ClassificationResult,
    SignificanceLevel,
)

logger = structlog.get_logger()

# Circuit breaker state — module-level, shared across tasks in the same worker process
_consecutive_failures = 0
_circuit_open_until: datetime | None = None
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 300  # 5 minutes

# Cost estimation: Sonnet pricing (as of 2024)
# Adjust these when model changes
COST_PER_INPUT_TOKEN = 3.0 / 1_000_000   # $3 per 1M input tokens
COST_PER_OUTPUT_TOKEN = 15.0 / 1_000_000  # $15 per 1M output tokens


def _check_circuit_breaker() -> bool:
    """Return True if the circuit is open (should NOT call Claude)."""
    global _circuit_open_until

    if _circuit_open_until is None:
        return False

    if datetime.now(timezone.utc) > _circuit_open_until:
        # Cooldown expired, try again
        _circuit_open_until = None
        return False

    return True


def _record_failure(is_retryable: bool):
    """Record a failure and trip the breaker if threshold reached."""
    global _consecutive_failures, _circuit_open_until

    if not is_retryable:
        _consecutive_failures += 1
        if _consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            _circuit_open_until = datetime.now(timezone.utc)
            from datetime import timedelta
            _circuit_open_until += timedelta(seconds=CIRCUIT_BREAKER_COOLDOWN_SECONDS)
            logger.error(
                "claude_circuit_breaker_open",
                consecutive_failures=_consecutive_failures,
                cooldown_seconds=CIRCUIT_BREAKER_COOLDOWN_SECONDS,
            )


def _record_success():
    """Reset failure counter on success."""
    global _consecutive_failures
    _consecutive_failures = 0


def classify_change(
    filtered_diff: str,
    competitor_name: str | None,
    page_type: str,
    url: str,
) -> dict:
    """Classify a change using Claude API.

    Returns:
        dict with:
            - classification: ClassificationResult dict (or None on failure)
            - prompt_tokens: int
            - completion_tokens: int
            - total_cost_usd: float
            - claude_model: str
            - needs_review: bool (True if classification was uncertain/fallback)
            - error: str | None
    """
    import anthropic

    # Check circuit breaker
    if _check_circuit_breaker():
        logger.warning("claude_circuit_breaker_open_skipping")
        return {
            "classification": _default_classification(),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_cost_usd": 0.0,
            "claude_model": settings.claude_model,
            "needs_review": True,
            "error": "Circuit breaker open — classification paused",
        }

    # Truncate diff to fit token budget
    diff_text, was_truncated = truncate_diff(filtered_diff)
    user_prompt = build_user_prompt(
        competitor_name=competitor_name,
        page_type=page_type,
        url=url,
        filtered_diff=diff_text,
        truncated=was_truncated,
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Define the tool schema for structured output
    tools = [
        {
            "name": "classify_change",
            "description": "Classify the significance of a detected competitor website change",
            "input_schema": {
                "type": "object",
                "properties": {
                    "significance_level": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low", "noise"],
                        "description": "How significant this change is",
                    },
                    "summary": {
                        "type": "string",
                        "maxLength": 1000,
                        "description": "Concise summary of what changed and why it matters",
                    },
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "pricing_change", "feature_launch", "feature_removal",
                                "hiring_signal", "messaging_change", "partnership",
                                "technical_change", "other",
                            ],
                        },
                        "minItems": 1,
                        "description": "Categories that describe the nature of the change",
                    },
                },
                "required": ["significance_level", "summary", "categories"],
            },
        }
    ]

    start_time = time.monotonic()

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=tools,
            tool_choice={"type": "tool", "name": "classify_change"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        duration_ms = int((time.monotonic() - start_time) * 1000)
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        total_cost = (prompt_tokens * COST_PER_INPUT_TOKEN) + (completion_tokens * COST_PER_OUTPUT_TOKEN)

        # Extract the tool use response
        tool_result = None
        for block in response.content:
            if block.type == "tool_use":
                tool_result = block.input
                break

        if tool_result is None:
            logger.warning("claude_no_tool_response", response_types=[b.type for b in response.content])
            # Fallback: try to parse from text blocks
            classification = _fallback_parse(response)
            needs_review = True
        else:
            # Validate through Pydantic
            try:
                parsed = ClassificationResult(**tool_result)
                classification = parsed.model_dump()
                needs_review = False
            except Exception as e:
                logger.warning("claude_schema_validation_failed", error=str(e), raw=tool_result)
                classification = _safe_parse_tool_result(tool_result)
                needs_review = True

        _record_success()

        logger.info(
            "claude_classification_complete",
            significance=classification.get("significance_level"),
            categories=classification.get("categories"),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=round(total_cost, 6),
            duration_ms=duration_ms,
            needs_review=needs_review,
        )

        return {
            "classification": classification,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_cost_usd": round(total_cost, 6),
            "claude_model": settings.claude_model,
            "needs_review": needs_review,
            "error": None,
        }

    except anthropic.AuthenticationError as e:
        _record_failure(is_retryable=False)
        logger.error("claude_auth_error", error=str(e))
        return _error_result(f"Authentication error: {e}", is_retryable=False)

    except anthropic.RateLimitError as e:
        _record_failure(is_retryable=True)
        logger.warning("claude_rate_limit", error=str(e))
        raise  # Let Celery retry handle this

    except anthropic.APIConnectionError as e:
        _record_failure(is_retryable=True)
        logger.warning("claude_connection_error", error=str(e))
        raise  # Let Celery retry handle this

    except anthropic.InternalServerError as e:
        _record_failure(is_retryable=True)
        logger.warning("claude_server_error", error=str(e))
        raise  # Let Celery retry handle this

    except Exception as e:
        _record_failure(is_retryable=True)
        logger.error("claude_unexpected_error", error=str(e), exc_info=True)
        return _error_result(f"Unexpected error: {e}", is_retryable=True)


def _default_classification() -> dict:
    """Safe default when classification fails."""
    return {
        "significance_level": "medium",
        "summary": "Classification failed — manual review required",
        "categories": ["other"],
    }


def _error_result(error_msg: str, is_retryable: bool) -> dict:
    """Return a result dict for failed classifications."""
    return {
        "classification": _default_classification(),
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_cost_usd": 0.0,
        "claude_model": settings.claude_model,
        "needs_review": True,
        "error": error_msg,
    }


def _safe_parse_tool_result(raw: dict) -> dict:
    """Best-effort parse of a tool result that failed Pydantic validation."""
    significance = raw.get("significance_level", "medium")
    if significance not in {"critical", "high", "medium", "low", "noise"}:
        significance = "medium"

    summary = raw.get("summary", "Classification uncertain — manual review required")
    if not isinstance(summary, str):
        summary = str(summary)

    categories = raw.get("categories", ["other"])
    if not isinstance(categories, list):
        categories = ["other"]

    valid_cats = {c.value for c in ChangeCategory}
    categories = [c for c in categories if c in valid_cats] or ["other"]

    return {
        "significance_level": significance,
        "summary": summary[:1000],
        "categories": categories,
    }


def _fallback_parse(response) -> dict:
    """Last-resort: extract classification from text blocks via regex.

    This handles the rare case where Claude responds with text instead
    of using the tool. We scan for keywords that match our enum values.
    """
    text_content = ""
    for block in response.content:
        if hasattr(block, "text"):
            text_content += block.text

    if not text_content:
        return _default_classification()

    # Try to find significance level
    significance = "medium"
    for level in ["critical", "high", "medium", "low", "noise"]:
        if re.search(rf"\b{level}\b", text_content, re.IGNORECASE):
            significance = level
            break

    # Try to find categories
    categories = []
    for cat in ChangeCategory:
        if cat.value.replace("_", " ") in text_content.lower() or cat.value in text_content.lower():
            categories.append(cat.value)
    if not categories:
        categories = ["other"]

    # Use the entire text as summary (truncated)
    summary = text_content[:1000].strip()

    return {
        "significance_level": significance,
        "summary": summary,
        "categories": categories,
    }
