import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.common.ids import uuid7
from app.database.base import Base, TimestampMixin


class UserSession(TimestampMixin, Base):
    """One row per logged-in device. Refresh tokens rotate; only hashes are stored."""

    __tablename__ = "user_sessions"
    __table_args__ = (Index("ix_user_sessions_user_active", "user_id", "revoked_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=uuid7)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # Previous hash kept to detect refresh-token reuse (theft) after rotation.
    previous_refresh_token_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    device_id: Mapped[str | None] = mapped_column(String(100))
    device_label: Mapped[str | None] = mapped_column(String(150))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    last_used_at: Mapped[datetime | None]
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    revoked_reason: Mapped[str | None] = mapped_column(String(50))
