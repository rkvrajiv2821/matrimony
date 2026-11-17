import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, SmallInteger, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.common.ids import uuid7
from app.common.time import utcnow
from app.database.base import Base
from app.profiles.options import ModerationStatus, Visibility


class ProfilePhoto(Base):
    """A processed, re-encoded profile photo. Originals are deleted after processing."""

    __tablename__ = "profile_photos"
    __table_args__ = (Index("ix_profile_photos_profile", "profile_id", "deleted_at", "sort_order"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=uuid7)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    storage_key: Mapped[str] = mapped_column(String(255))
    thumbnail_key: Mapped[str] = mapped_column(String(255))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)
    is_primary: Mapped[bool] = mapped_column(default=False)
    visibility: Mapped[str] = mapped_column(String(20), default=Visibility.MEMBERS)
    moderation_status: Mapped[str] = mapped_column(
        String(20), default=ModerationStatus.PENDING, index=True
    )
    moderation_reason: Mapped[str | None] = mapped_column(String(50))
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    deleted_at: Mapped[datetime | None]
