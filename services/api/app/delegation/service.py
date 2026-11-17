"""Family delegation (PRD §3, §6.2).

Two flows share `delegated_access`:
- SUBJECT_CONSENT: a relative creates a profile for an adult. Nothing can be edited until the
  adult logs in with their own phone and accepts; they then own the profile and choose the
  relative's scope.
- HELPER_INVITE: an owner invites a relative to help, with a chosen scope. Revocable at any time.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.auth.sms import get_sms_provider
from app.common.errors import AppError, Conflict, NotFound, PermissionDenied
from app.common.time import utcnow
from app.delegation.models import (
    ALL_SCOPES,
    DelegatedAccess,
    DelegationKind,
    DelegationStatus,
)
from app.profiles.models import Profile
from app.profiles.options import ProfileStatus
from app.security.deps import RequestMeta
from app.users.models import User

MAX_PENDING_CREATIONS = 5
MAX_HELPERS = 3


async def notify_invite(phone: str, kind: DelegationKind, inviter_name: str) -> None:
    await get_sms_provider().send_notice(
        phone, f"delegation.{kind.value}", {"inviter": inviter_name[:40]}
    )


async def count_pending_creations(db: AsyncSession, user: User) -> int:
    return int(
        await db.scalar(
            select(func.count())
            .select_from(DelegatedAccess)
            .where(
                DelegatedAccess.invited_by_user_id == user.id,
                DelegatedAccess.kind == DelegationKind.SUBJECT_CONSENT,
                DelegatedAccess.status == DelegationStatus.INVITED,
            )
        )
        or 0
    )


async def invite_helper(
    db: AsyncSession,
    profile: Profile,
    owner: User,
    phone: str,
    relationship: str,
    scopes: list[str],
    meta: RequestMeta,
) -> DelegatedAccess:
    if phone == owner.phone_e164:
        raise AppError("You can't invite yourself.", code="invalid_invitee")
    current = list(
        await db.scalars(
            select(DelegatedAccess).where(
                DelegatedAccess.profile_id == profile.id,
                DelegatedAccess.kind == DelegationKind.HELPER_INVITE,
                DelegatedAccess.status.in_([DelegationStatus.INVITED, DelegationStatus.ACTIVE]),
            )
        )
    )
    if len(current) >= MAX_HELPERS:
        raise Conflict("You can have up to 3 family helpers.", code="too_many_helpers")
    if any(d.invited_phone_e164 == phone for d in current):
        raise Conflict("This person is already invited.", code="already_invited")
    row = DelegatedAccess(
        profile_id=profile.id,
        kind=DelegationKind.HELPER_INVITE,
        invited_phone_e164=phone,
        invited_by_user_id=owner.id,
        relationship=relationship,
        permission_scope=scopes,
        status=DelegationStatus.INVITED,
    )
    db.add(row)
    await db.flush()
    await audit.record(
        db,
        action="delegation.invite",
        resource_type="profile",
        resource_id=str(profile.public_id),
        actor_user_id=owner.id,
        after={"delegation": str(row.public_id), "scopes": scopes, "relationship": relationship},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    await notify_invite(phone, DelegationKind.HELPER_INVITE, profile.subject_name)
    return row


async def invitation_for(db: AsyncSession, user: User, public_id: object) -> DelegatedAccess:
    row = await db.scalar(
        select(DelegatedAccess)
        .where(
            DelegatedAccess.public_id == public_id,
            DelegatedAccess.invited_phone_e164 == user.phone_e164,  # only the invited phone
            DelegatedAccess.status == DelegationStatus.INVITED,
        )
        .with_for_update()
    )
    if row is None:
        raise NotFound()
    return row


async def accept(
    db: AsyncSession, user: User, row: DelegatedAccess, scopes: list[str] | None, meta: RequestMeta
) -> Profile:
    profile = await db.get(Profile, row.profile_id, with_for_update=True)
    if profile is None or profile.profile_status == ProfileStatus.ARCHIVED:
        raise NotFound()
    now = utcnow()
    if row.kind == DelegationKind.SUBJECT_CONSENT:
        if profile.owner_user_id is not None:
            raise NotFound()
        if await db.scalar(select(Profile.id).where(Profile.owner_user_id == user.id)):
            raise Conflict(
                "You already have a profile. Ask your family member to help with that one instead.",
                code="profile_exists",
            )
        profile.owner_user_id = user.id
        profile.subject_phone_e164 = None
        # The adult decides how much the relative who created the profile may do.
        row.permission_scope = scopes if scopes is not None else list(ALL_SCOPES)
    else:
        if profile.owner_user_id == user.id:
            raise AppError("You already own this profile.", code="invalid_invitee")
        row.delegate_user_id = user.id
        row.permission_scope = row.permission_scope if scopes is None else scopes
    row.status = DelegationStatus.ACTIVE
    row.accepted_at = now
    row.invited_phone_e164 = None
    await audit.record(
        db,
        action=f"delegation.accept.{row.kind}",
        resource_type="profile",
        resource_id=str(profile.public_id),
        actor_user_id=user.id,
        after={"delegation": str(row.public_id), "scopes": row.permission_scope},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    await db.flush()
    return profile


async def decline(db: AsyncSession, user: User, row: DelegatedAccess, meta: RequestMeta) -> None:
    row.status = DelegationStatus.DECLINED
    row.revoked_at = utcnow()
    profile = await db.get(Profile, row.profile_id, with_for_update=True)
    if row.kind == DelegationKind.SUBJECT_CONSENT and profile and profile.owner_user_id is None:
        # The adult said no: the relative's draft is closed and never published.
        await _archive_unclaimed(db, profile, user, meta)
    await audit.record(
        db,
        action=f"delegation.decline.{row.kind}",
        resource_type="profile",
        resource_id=str(profile.public_id) if profile else None,
        actor_user_id=user.id,
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )


async def _archive_unclaimed(
    db: AsyncSession, profile: Profile, actor: User, meta: RequestMeta
) -> None:
    from app.profiles.service import transition

    await transition(
        db,
        profile,
        ProfileStatus.ARCHIVED,
        by="member",
        actor=actor,
        meta=meta,
        reason_code="subject_declined",
    )


async def revoke(
    db: AsyncSession, user: User, row: DelegatedAccess, profile: Profile, meta: RequestMeta
) -> None:
    """Owner removes a helper, a helper leaves, or a creator withdraws an unaccepted profile."""
    is_owner = profile.owner_user_id == user.id
    is_self = row.delegate_user_id == user.id
    is_pending_creator = (
        row.kind == DelegationKind.SUBJECT_CONSENT
        and row.status == DelegationStatus.INVITED
        and row.invited_by_user_id == user.id
    )
    if not (is_owner or is_self or is_pending_creator):
        raise PermissionDenied()
    row.status = DelegationStatus.REVOKED
    row.revoked_at = utcnow()
    if is_pending_creator and profile.owner_user_id is None:
        await _archive_unclaimed(db, profile, user, meta)
    await audit.record(
        db,
        action="delegation.revoke",
        resource_type="profile",
        resource_id=str(profile.public_id),
        actor_user_id=user.id,
        after={"delegation": str(row.public_id)},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
