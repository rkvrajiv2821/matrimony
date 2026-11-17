import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.common.ids import uuid7
from app.database.base import Base


class ConsentType(StrEnum):
    TERMS = "terms"
    PRIVACY = "privacy"
    MARKETING = "marketing"
    WHATSAPP = "whatsapp"


REQUIRED_CONSENTS = frozenset({ConsentType.TERMS, ConsentType.PRIVACY})


class Consent(Base):
    """Append-only consent history. Withdrawal sets withdrawn_at; rows are never deleted."""

    __tablename__ = "consents"
    __table_args__ = (Index("ix_consents_user_type", "user_id", "consent_type", "withdrawn_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=uuid7)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    consent_type: Mapped[str] = mapped_column(String(30))
    policy_version: Mapped[str] = mapped_column(String(30))
    granted: Mapped[bool]
    source: Mapped[str] = mapped_column(String(30))
    granted_at: Mapped[datetime]
    withdrawn_at: Mapped[datetime | None]
