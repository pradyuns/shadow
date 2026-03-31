import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Monitor(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "monitors"
    __table_args__ = (UniqueConstraint("user_id", "url", name="uq_monitors_user_url"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    competitor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_type: Mapped[str] = mapped_column(String(50), nullable=False)
    render_js: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    use_firecrawl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    check_interval_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    next_check_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_scrape_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    last_scrape_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_snapshot_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    last_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    noise_patterns: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    css_selector: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="monitors")
    alerts = relationship("Alert", back_populates="monitor", cascade="all, delete-orphan")
