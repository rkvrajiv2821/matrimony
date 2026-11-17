"""Plan / entitlement tables (PRD v1.1 §4.2).

At launch only the `free` plan exists and it grants every core entitlement.
Orders, payments, refunds and invoices arrive with the dormant monetization module.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class Plan(TimestampMixin, Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    active: Mapped[bool] = mapped_column(default=True)


class PlanVersion(TimestampMixin, Base):
    """Immutable once published: prices are always computed server-side from a version."""

    __tablename__ = "plan_versions"
    __table_args__ = (UniqueConstraint("plan_id", "version"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    version: Mapped[int]
    amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    duration_days: Mapped[int | None]
    tax_config_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    effective_from: Mapped[datetime]
    effective_to: Mapped[datetime | None]


class PlanEntitlement(Base):
    __tablename__ = "plan_entitlements"
    __table_args__ = (UniqueConstraint("plan_version_id", "entitlement_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_version_id: Mapped[int] = mapped_column(ForeignKey("plan_versions.id", ondelete="CASCADE"))
    entitlement_key: Mapped[str] = mapped_column(String(100))
    value_json: Mapped[Any] = mapped_column(JSON)


class UserEntitlement(TimestampMixin, Base):
    __tablename__ = "user_entitlements"
    __table_args__ = (Index("ix_user_entitlements_lookup", "user_id", "status", "entitlement_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    entitlement_key: Mapped[str] = mapped_column(String(100))
    value_json: Mapped[Any] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(50))
    starts_at: Mapped[datetime]
    expires_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(String(20), default="active")
