import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class AlertRead(BaseModel):
    id: uuid.UUID
    monitor_id: uuid.UUID
    severity: str
    summary: str
    categories: list
    is_acknowledged: bool
    notified_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertDetail(AlertRead):
    user_id: uuid.UUID
    diff_id: str
    analysis_id: str
    acknowledged_at: datetime | None
    notified_via_slack: bool
    notified_via_email: bool
    notification_error: str | None
