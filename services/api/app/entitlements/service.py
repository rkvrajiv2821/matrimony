"""Entitlement resolution.

Every member feature check goes through `has_entitlement` / `require_entitlement`, so a
future paid plan is a data change, not a code change (PRD v1.1 §2).

Safety, privacy, reporting, blocking, support and account deletion must NEVER call this
module (PRD v1.1 §5) — enforced by tests/test_entitlements.py::test_safety_modules_never_gated.
"""

from enum import StrEnum
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import PermissionDenied
from app.common.time import utcnow
from app.entitlements.models import Plan, PlanEntitlement, PlanVersion, UserEntitlement
from app.users.models import User

DEFAULT_PLAN_CODE = "free"


class Entitlement(StrEnum):
    PROFILE_CREATE = "profile.create"
    SEARCH_USE = "search.use"
    RECOMMENDATIONS_VIEW = "recommendations.view"
    SHORTLIST_USE = "shortlist.use"
    INTERESTS_SEND = "interests.send"
    MESSAGING_SEND = "messaging.send"
    HOROSCOPE_DETAILS = "horoscope.details"


# Core keys every member must hold at launch. The `free` plan seeds all of them.
CORE_ENTITLEMENTS: frozenset[str] = frozenset(e.value for e in Entitlement)


async def _default_plan_entitlements(db: AsyncSession) -> dict[str, Any]:
    now = utcnow()
    stmt = (
        select(PlanEntitlement.entitlement_key, PlanEntitlement.value_json)
        .join(PlanVersion, PlanVersion.id == PlanEntitlement.plan_version_id)
        .join(Plan, Plan.id == PlanVersion.plan_id)
        .where(
            Plan.code == DEFAULT_PLAN_CODE,
            Plan.active.is_(True),
            PlanVersion.effective_from <= now,
            or_(PlanVersion.effective_to.is_(None), PlanVersion.effective_to > now),
        )
    )
    return {k: v for k, v in (await db.execute(stmt)).all()}


async def resolve(db: AsyncSession, user: User) -> dict[str, Any]:
    """Default-plan entitlements overlaid with the user's active, unexpired grants."""
    result = await _default_plan_entitlements(db)
    now = utcnow()
    stmt = select(UserEntitlement.entitlement_key, UserEntitlement.value_json).where(
        UserEntitlement.user_id == user.id,
        UserEntitlement.status == "active",
        UserEntitlement.starts_at <= now,
        or_(UserEntitlement.expires_at.is_(None), UserEntitlement.expires_at > now),
    )
    for key, value in (await db.execute(stmt)).all():
        result[key] = value
    return result


def _granted(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value.get("enabled", True))
    return bool(value)


async def has_entitlement(db: AsyncSession, user: User, key: Entitlement | str) -> bool:
    return _granted((await resolve(db, user)).get(str(key)))


async def require_entitlement(db: AsyncSession, user: User, key: Entitlement | str) -> None:
    if not await has_entitlement(db, user, key):
        # Generic message: no pricing or upsell prompts while monetization is off.
        raise PermissionDenied("This feature is not available.", code="feature_unavailable")
