from datetime import datetime

from pydantic import BaseModel


class DiffRead(BaseModel):
    id: str
    monitor_id: str
    diff_lines_added: int
    diff_lines_removed: int
    is_empty_after_filter: bool
    noise_lines_removed: int
    created_at: datetime


class DiffDetail(DiffRead):
    snapshot_before_id: str
    snapshot_after_id: str
    unified_diff: str
    filtered_diff: str | None
    diff_size_bytes: int
