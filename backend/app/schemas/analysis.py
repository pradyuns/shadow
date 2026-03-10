from datetime import datetime

from pydantic import BaseModel


class AnalysisRead(BaseModel):
    id: str
    diff_id: str
    monitor_id: str
    significance_level: str
    summary: str
    categories: list[str]
    claude_model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_cost_usd: float | None
    needs_review: bool
    created_at: datetime
