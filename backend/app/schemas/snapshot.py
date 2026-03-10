from datetime import datetime

from pydantic import BaseModel


class SnapshotRead(BaseModel):
    id: str
    monitor_id: str
    url: str
    http_status: int | None
    render_method: str | None
    text_hash: str | None
    fetch_duration_ms: int | None
    status: str | None
    is_baseline: bool
    created_at: datetime


class SnapshotDetail(SnapshotRead):
    extracted_text: str | None
    raw_html: str | None = None
