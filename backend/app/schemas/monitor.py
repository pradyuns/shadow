import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class PageType(str, Enum):
    pricing = "pricing"
    changelog = "changelog"
    homepage = "homepage"
    jobs = "jobs"
    blog = "blog"
    docs = "docs"
    other = "other"


class MonitorCreate(BaseModel):
    url: HttpUrl
    name: str = Field(min_length=1, max_length=255)
    competitor_name: str | None = Field(default=None, max_length=255)
    page_type: PageType
    render_js: bool = False
    check_interval_hours: int = Field(default=6, ge=1, le=168)
    css_selector: str | None = None
    noise_patterns: list[str] = Field(default_factory=list)


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    competitor_name: str | None = None
    page_type: PageType | None = None
    render_js: bool | None = None
    check_interval_hours: int | None = Field(default=None, ge=1, le=168)
    is_active: bool | None = None
    css_selector: str | None = None
    noise_patterns: list[str] | None = None


class MonitorRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    url: str
    name: str
    competitor_name: str | None
    page_type: str
    render_js: bool
    check_interval_hours: int
    is_active: bool
    next_check_at: datetime
    last_checked_at: datetime | None
    last_scrape_status: str
    last_scrape_error: str | None
    last_snapshot_id: str | None
    last_change_at: datetime | None
    consecutive_failures: int
    noise_patterns: list
    css_selector: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
