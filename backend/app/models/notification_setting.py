import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class NotificationSetting(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notification_settings"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", name="uq_notification_settings_user_channel"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    digest_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    digest_hour_utc: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="notification_settings")
