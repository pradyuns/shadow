"""Alert cluster — groups related alerts from the same competitive event.

When a competitor launches a product, they often update pricing, changelog, docs,
and hiring pages simultaneously. Instead of showing 5 separate alerts, clustering
detects that these changes are part of one event and groups them.

The clustering algorithm uses temporal proximity, category overlap, and keyword
similarity to decide whether a new alert belongs to an existing cluster.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class AlertCluster(UUIDMixin, Base):
    __tablename__ = "alert_clusters"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    competitor_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    summary_keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    alerts = relationship("Alert", back_populates="cluster", lazy="selectin")
