from datetime import datetime

from pydantic import BaseModel, Field


class LearnedPatternExample(BaseModel):
    before: str
    after: str
    diff_id: str | None = None
    seen_at: datetime | None = None


class LearnedNoisePatternRead(BaseModel):
    id: str
    pattern: str
    template: str
    support_count: int
    confidence: float
    decay_score: float
    is_active: bool
    manual_review_required: bool
    blocked_reason: str | None = None
    lines_filtered_7d: int = 0
    total_lines_filtered: int = 0
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    last_matched_at: datetime | None = None
    examples: list[LearnedPatternExample] = Field(default_factory=list)


class MonitorNoiseLearningRead(BaseModel):
    monitor_id: str
    monitor_name: str
    learned_patterns: int
    active_patterns: int
    manual_review_patterns: int
    lines_filtered_7d: int
    total_lines_filtered: int
    avg_confidence: float
    patterns: list[LearnedNoisePatternRead] = Field(default_factory=list)


class NoiseLearningOverviewItem(BaseModel):
    monitor_id: str
    monitor_name: str
    competitor_name: str | None = None
    learned_patterns: int
    active_patterns: int
    manual_review_patterns: int
    lines_filtered_7d: int
    avg_confidence: float

