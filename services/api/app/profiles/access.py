"""Who may manage a profile, and with which scopes (resource-level authorization)."""

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import Conflict, NotFound, PermissionDenied
from app.delegation.models import ALL_SCOPES, DelegatedAccess, DelegationStatus, Scope
from app.profiles.models import Profile
from app.profiles.options import ProfileStatus
from app.users.models import User


class ManagerRole(StrEnum):
    OWNER = "owner"
    DELEGATE = "delegate"
    # Family member who created the profile; the subject has not consented yet. View only.
    CREATOR_PENDING = "creator_pending"
    # Moderation staff reviewing the profile (read-only through this path).
    STAFF = "staff"


@dataclass
class Managed:
    profile: Profile
    role: ManagerRole
    scopes: set[str] = field(default_factory=set)

    def require(self, scope: Scope) -> None:
        if self.role == ManagerRole.CREATOR_PENDING:
            raise Conflict(
                "The person this profile is for has not accepted the invitation yet.",
                code="subject_consent_pending",
            )
        if scope.value not in self.scopes:
            raise PermissionDenied(
                "You don't have permission for this part of the profile.", code="delegation_scope"
            )

    def require_owner(self) -> None:
        if self.role != ManagerRole.OWNER:
            raise PermissionDenied("Only the profile owner can do this.", code="owner_only")

    def require_editable(self) -> None:
        if self.profile.profile_status in (ProfileStatus.SUSPENDED, ProfileStatus.ARCHIVED):
            raise Conflict("This profile can't be changed right now.", code="profile_locked")


async def role_for(db: AsyncSession, user: User, profile: Profile) -> Managed | None:
    if profile.owner_user_id == user.id:
        return Managed(profile, ManagerRole.OWNER, set(ALL_SCOPES))
    delegation = await db.scalar(
        select(DelegatedAccess).where(
            DelegatedAccess.profile_id == profile.id,
            DelegatedAccess.delegate_user_id == user.id,
            DelegatedAccess.status == DelegationStatus.ACTIVE,
        )
    )
    if delegation is not None and profile.owner_user_id is not None:
        return Managed(profile, ManagerRole.DELEGATE, set(delegation.permission_scope))
    if profile.owner_user_id is None and profile.created_by_user_id == user.id:
        return Managed(profile, ManagerRole.CREATOR_PENDING)
    return None


async def load_managed(
    db: AsyncSession, user: User, profile_public_id: uuid.UUID, *, for_update: bool = False
) -> Managed:
    """Return the profile if `user` manages it; otherwise 404 (never reveal existence)."""
    stmt = select(Profile).where(Profile.public_id == profile_public_id)
    if for_update:
        stmt = stmt.with_for_update()
    profile = await db.scalar(stmt)
    if profile is None or profile.profile_status == ProfileStatus.ARCHIVED:
        raise NotFound()
    managed = await role_for(db, user, profile)
    if managed is None:
        raise NotFound()
    return managed


async def managed_profiles(db: AsyncSession, user: User) -> list[Managed]:
    delegated_ids = select(DelegatedAccess.profile_id).where(
        DelegatedAccess.delegate_user_id == user.id,
        DelegatedAccess.status == DelegationStatus.ACTIVE,
    )
    rows = await db.scalars(
        select(Profile)
        .where(
            Profile.profile_status != ProfileStatus.ARCHIVED,
            or_(
                Profile.owner_user_id == user.id,
                Profile.id.in_(delegated_ids),
                (Profile.owner_user_id.is_(None)) & (Profile.created_by_user_id == user.id),
            ),
        )
        .order_by(Profile.id)
    )
    result = []
    for profile in rows:
        managed = await role_for(db, user, profile)
        if managed is not None:
            result.append(managed)
    return result
