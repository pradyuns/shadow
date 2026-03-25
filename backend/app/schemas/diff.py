from datetime import datetime

from pydantic import BaseModel, Field


class DiffRead(BaseModel):
    id: str
    monitor_id: str
    diff_lines_added: int
    diff_lines_removed: int
    is_empty_after_filter: bool
    noise_lines_removed: int = 0
    learned_noise_lines_removed: int = 0
    learned_noise_pattern_hits: dict[str, int] = Field(default_factory=dict)
    created_at: datetime


class DiffDetail(DiffRead):
    snapshot_before_id: str
    snapshot_after_id: str
    unified_diff: str
    filtered_diff: str | None
    diff_size_bytes: int
