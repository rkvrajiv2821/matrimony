from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.time import utcnow
from app.database.base import Base


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    enabled: Mapped[bool] = mapped_column(default=False)
    rollout_percent: Mapped[int] = mapped_column(SmallInteger, default=0)
    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(String(255), default="")
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[Any] = mapped_column(JSON)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
