"""Pydantic schemas for Claude classification responses.

These schemas serve dual purpose:
1. Structured output schema sent to Claude (via tool_use)
2. Validation of Claude's response before storage

Why Pydantic over plain dicts:
- Type safety and validation built-in
- Default values for missing fields (resilience against Claude hiccups)
- Enum validation catches invalid significance levels automatically
"""

from enum import Enum

from pydantic import BaseModel, Field


class SignificanceLevel(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    noise = "noise"


class ChangeCategory(str, Enum):
    pricing_change = "pricing_change"
    feature_launch = "feature_launch"
    feature_removal = "feature_removal"
    hiring_signal = "hiring_signal"
    messaging_change = "messaging_change"
    partnership = "partnership"
    technical_change = "technical_change"
    other = "other"


class ClassificationResult(BaseModel):
    """The expected response shape from Claude's classification."""

    significance_level: SignificanceLevel = Field(
        description="How significant this change is for competitive intelligence"
    )
    summary: str = Field(
        max_length=1000, description="Concise summary of what changed and why it matters (max 200 words)"
    )
    categories: list[ChangeCategory] = Field(
        min_length=1, description="One or more categories that describe the nature of the change"
    )


# Severity ordering for comparison (used in alert suppression)
SEVERITY_ORDER = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "noise": 0,
}
