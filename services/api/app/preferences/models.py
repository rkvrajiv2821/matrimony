import uuid
from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, SmallInteger, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.ids import uuid7
from app.database.base import Base, TimestampMixin


class PartnerPreference(TimestampMixin, Base):
    """Partner preferences (PRD §4.3).

    Each criterion is classified by the member as must-have, preferred or flexible. Ranges and
    single-choice criteria live in columns; list criteria and their classification live in JSON:

        location_rules = {"district_ids": [..], "countries": ["IN"]}
        must_have / preferred = ["age", "marital_status", "district", ...]  (criterion keys)
        excluded = {"diet": ["non_vegetarian"], ...}
    """

    __tablename__ = "partner_preferences"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=uuid7)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(60), default="Default")
    is_default: Mapped[bool] = mapped_column(default=True)
    age_min: Mapped[int | None] = mapped_column(SmallInteger)
    age_max: Mapped[int | None] = mapped_column(SmallInteger)
    height_min_cm: Mapped[int | None] = mapped_column(SmallInteger)
    height_max_cm: Mapped[int | None] = mapped_column(SmallInteger)
    marital_statuses: Mapped[list[str] | None] = mapped_column(JSON)
    location_rules: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    education_levels: Mapped[list[str] | None] = mapped_column(JSON)
    employment_types: Mapped[list[str] | None] = mapped_column(JSON)
    income_bands: Mapped[list[str] | None] = mapped_column(JSON)
    diets: Mapped[list[str] | None] = mapped_column(JSON)
    mother_tongues: Mapped[list[str] | None] = mapped_column(JSON)
    must_have: Mapped[list[str] | None] = mapped_column(JSON)
    preferred: Mapped[list[str] | None] = mapped_column(JSON)
    excluded: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(default=True)

    community_values: Mapped[list["PreferenceCommunityValue"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )


class PreferenceCommunityValue(Base):
    __tablename__ = "preference_community_values"

    preference_id: Mapped[int] = mapped_column(
        ForeignKey("partner_preferences.id", ondelete="CASCADE"), primary_key=True
    )
    community_id: Mapped[int] = mapped_column(
        ForeignKey("community_taxonomy.id", ondelete="RESTRICT"), primary_key=True
    )
    preference_type: Mapped[str] = mapped_column(String(20), default="preferred")
