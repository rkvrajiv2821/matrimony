import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.common.ids import uuid7
from app.common.time import utcnow
from app.database.base import Base


class DelegationKind(StrEnum):
    # A family member created the profile and the adult subject must consent (PRD §6.2).
    SUBJECT_CONSENT = "subject_consent"
    # The subject invites a family member to help manage their profile.
    HELPER_INVITE = "helper_invite"


class DelegationStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DECLINED = "declined"
    REVOKED = "revoked"


class Scope(StrEnum):
    EDIT_PROFILE = "edit_profile"
    MANAGE_PHOTOS = "manage_photos"
    MANAGE_PREFERENCES = "manage_preferences"


ALL_SCOPES: list[str] = [s.value for s in Scope]


class DelegatedAccess(Base):
    """A family member's scoped, revocable access to someone else's profile.

    `delegate_user_id` is the helper. For HELPER_INVITE rows it is NULL until the invited phone
    accepts. For SUBJECT_CONSENT rows the helper is the creator and `invited_phone_e164` is the
    subject's phone; accepting makes the subject the profile owner.
    """

    __tablename__ = "delegated_access"
    __table_args__ = (
        Index("ix_delegated_access_profile", "profile_id", "status"),
        Index("ix_delegated_access_delegate", "delegate_user_id", "status"),
        Index("ix_delegated_access_invited_phone", "invited_phone_e164", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=uuid7)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))
    delegate_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    invited_phone_e164: Mapped[str | None] = mapped_column(String(16))
    invited_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    relationship: Mapped[str] = mapped_column(String(20))
    permission_scope: Mapped[list[str]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default=DelegationStatus.INVITED)
    invited_at: Mapped[datetime] = mapped_column(default=utcnow)
    accepted_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]
