import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.ids import uuid7
from app.common.time import utcnow
from app.database.base import Base, TimestampMixin
from app.profiles.options import ProfileStatus, ProfileVisibility, Visibility


class Profile(TimestampMixin, Base):
    """A matrimonial profile about one adult (the *subject*).

    `owner_user_id` is the subject's own account. A family member may create the profile first;
    until the subject accepts (PRD §6.2) the owner is NULL and only `created_by_user_id` is set.
    """

    __tablename__ = "profiles"
    __table_args__ = (
        Index("ix_profiles_discovery", "profile_status", "visibility", "gender", "date_of_birth"),
        Index("ix_profiles_location", "state_id", "district_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=uuid7)
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Phone of the adult subject while their consent is pending (never shown to members).
    subject_phone_e164: Mapped[str | None] = mapped_column(String(16), index=True)
    created_for: Mapped[str] = mapped_column(String(20))
    subject_name: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str | None] = mapped_column(String(60))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(10))
    marital_status: Mapped[str | None] = mapped_column(String(30))
    has_children: Mapped[bool | None]
    height_cm: Mapped[int | None] = mapped_column(SmallInteger)
    mother_tongue: Mapped[str | None] = mapped_column(String(30))
    current_country: Mapped[str | None] = mapped_column(String(2))
    state_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"))
    district_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"))
    city_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"))
    profile_status: Mapped[str] = mapped_column(String(20), default=ProfileStatus.DRAFT)
    status_reason_code: Mapped[str | None] = mapped_column(String(50))
    status_note: Mapped[str | None] = mapped_column(String(500))
    visibility: Mapped[str] = mapped_column(String(20), default=ProfileVisibility.DISCOVERABLE)
    completion_percent: Mapped[int] = mapped_column(SmallInteger, default=0)
    submitted_at: Mapped[datetime | None]
    approved_at: Mapped[datetime | None]

    personal: Mapped["ProfilePersonalDetails | None"] = relationship(
        lazy="selectin", cascade="all, delete-orphan", uselist=False
    )
    family: Mapped["ProfileFamilyDetails | None"] = relationship(
        lazy="selectin", cascade="all, delete-orphan", uselist=False
    )
    education: Mapped["ProfileEducation | None"] = relationship(
        lazy="selectin", cascade="all, delete-orphan", uselist=False
    )
    employment: Mapped["ProfileEmployment | None"] = relationship(
        lazy="selectin", cascade="all, delete-orphan", uselist=False
    )
    communities: Mapped[list["ProfileCommunity"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )


class ProfilePersonalDetails(Base):
    __tablename__ = "profile_personal_details"

    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    physical_status: Mapped[str | None] = mapped_column(String(30))
    languages: Mapped[list[str] | None] = mapped_column(JSON)
    about_me: Mapped[str | None] = mapped_column(Text)
    diet: Mapped[str | None] = mapped_column(String(20))
    smoking: Mapped[str | None] = mapped_column(String(20))
    drinking: Mapped[str | None] = mapped_column(String(20))
    hobbies: Mapped[list[str] | None] = mapped_column(JSON)
    interests: Mapped[list[str] | None] = mapped_column(JSON)


class ProfileCommunity(Base):
    __tablename__ = "profile_community"

    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    community_id: Mapped[int] = mapped_column(
        ForeignKey("community_taxonomy.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    is_primary: Mapped[bool] = mapped_column(default=False)
    visibility: Mapped[str] = mapped_column(String(20), default=Visibility.MEMBERS)


class ProfileFamilyDetails(Base):
    __tablename__ = "profile_family_details"

    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    family_type: Mapped[str | None] = mapped_column(String(20))
    family_values: Mapped[str | None] = mapped_column(String(20))
    native_district_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL")
    )
    father_occupation: Mapped[str | None] = mapped_column(String(100))
    mother_occupation: Mapped[str | None] = mapped_column(String(100))
    siblings_count: Mapped[int | None] = mapped_column(SmallInteger)
    siblings_married: Mapped[int | None] = mapped_column(SmallInteger)
    family_description: Mapped[str | None] = mapped_column(String(1000))
    visibility: Mapped[str] = mapped_column(String(20), default=Visibility.MEMBERS)


class ProfileEducation(Base):
    """Highest qualification. The table allows several rows; the MVP keeps one per profile."""

    __tablename__ = "profile_education"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), unique=True
    )
    qualification: Mapped[str] = mapped_column(String(30))
    field_of_study: Mapped[str | None] = mapped_column(String(30))
    institution: Mapped[str | None] = mapped_column(String(150))
    year_completed: Mapped[int | None] = mapped_column(SmallInteger)
    visibility: Mapped[str] = mapped_column(String(20), default=Visibility.MEMBERS)


class ProfileEmployment(Base):
    __tablename__ = "profile_employment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), unique=True
    )
    employment_type: Mapped[str] = mapped_column(String(30))
    occupation: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(30))
    employer: Mapped[str | None] = mapped_column(String(150))
    work_city_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL")
    )
    income_band: Mapped[str | None] = mapped_column(String(20))
    # Applies to employer and income; occupation/industry are always member-visible.
    visibility: Mapped[str] = mapped_column(String(20), default=Visibility.MEMBERS)


class ProfileStatusHistory(Base):
    __tablename__ = "profile_status_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    reason_code: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(String(500))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


def jsonable(value: Any) -> Any:
    """Make date/uuid values JSON-safe for audit before/after snapshots."""
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value
