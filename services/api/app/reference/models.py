from enum import StrEnum

from sqlalchemy import BigInteger, ForeignKey, Index, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class LocationType(StrEnum):
    COUNTRY = "country"
    STATE = "state"
    DISTRICT = "district"
    CITY = "city"


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (Index("ix_locations_parent_type", "parent_id", "type", "active"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"))
    type: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name_en: Mapped[str] = mapped_column(String(100))
    name_ta: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(default=True)


class TaxonomyType(StrEnum):
    COMMUNITY = "community"
    SUB_COMMUNITY = "sub_community"


class CommunityTaxonomy(Base):
    """Admin-configurable community labels (PRD §4.2, §9). Launch values are placeholders."""

    __tablename__ = "community_taxonomy"
    __table_args__ = (UniqueConstraint("type", "code"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("community_taxonomy.id", ondelete="RESTRICT")
    )
    type: Mapped[str] = mapped_column(String(30))
    code: Mapped[str] = mapped_column(String(50))
    label_en: Mapped[str] = mapped_column(String(150))
    label_ta: Mapped[str] = mapped_column(String(150))
    active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)
