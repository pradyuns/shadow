from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class BetaSignup(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "beta_signups"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="landing_page", server_default="landing_page"
    )
