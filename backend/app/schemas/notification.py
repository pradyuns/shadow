import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Channel(str, Enum):
    slack = "slack"
    email = "email"


class NotificationSettingUpdate(BaseModel):
    is_enabled: bool = True
    min_severity: str = "medium"
    slack_webhook_url: str | None = None
    email_address: str | None = None
    digest_mode: bool = False
    digest_hour_utc: int | None = Field(default=None, ge=0, le=23)


class NotificationSettingRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    channel: str
    is_enabled: bool
    min_severity: str
    slack_webhook_url: str | None
    email_address: str | None
    digest_mode: bool
    digest_hour_utc: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
