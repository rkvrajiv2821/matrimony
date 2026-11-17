import uuid
from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.common.errors import NotFound
from app.common.phone import mask_phone, normalize_phone
from app.delegation import service
from app.delegation.models import (
    DelegatedAccess,
    DelegationKind,
    DelegationStatus,
    Scope,
)
from app.profiles.access import load_managed
from app.profiles.models import Profile
from app.profiles.options import CreatedFor
from app.profiles.schemas import DelegateSummary
from app.security.deps import DB, Auth, Meta
from app.users.models import User

router = APIRouter(tags=["delegation"])


class ScopesIn(BaseModel):
    scopes: list[Scope] = Field(max_length=len(Scope))

    @field_validator("scopes")
    @classmethod
    def _dedupe(cls, v: list[Scope]) -> list[Scope]:
        return list(dict.fromkeys(v))


class HelperInviteIn(ScopesIn):
    phone: str = Field(max_length=20)
    relationship: CreatedFor


class AcceptIn(BaseModel):
    # For subject consent: which permissions the relative who created the profile keeps.
    scopes: list[Scope] | None = None


class InvitationOut(BaseModel):
    id: uuid.UUID
    kind: DelegationKind
    relationship: str
    subject_name: str
    profile_display_name: str | None
    proposed_scopes: list[Scope]
    invited_by_phone_masked: str | None
    invited_at: datetime


async def _summary(db: DB, row: DelegatedAccess, me: User) -> DelegateSummary:
    phone = row.invited_phone_e164
    if phone is None and row.delegate_user_id is not None:
        delegate = await db.get(User, row.delegate_user_id)
        phone = delegate.phone_e164 if delegate else None
    return DelegateSummary(
        id=row.public_id,
        relationship=row.relationship,
        status=row.status,
        scopes=[Scope(s) for s in row.permission_scope],
        phone_masked=mask_phone(phone) if phone else None,
        is_me=row.delegate_user_id == me.id,
    )


@router.get("/delegations/invitations", response_model=list[InvitationOut])
async def my_invitations(auth: Auth, db: DB) -> list[InvitationOut]:
    rows = (
        await db.execute(
            select(DelegatedAccess, Profile)
            .join(Profile, Profile.id == DelegatedAccess.profile_id)
            .where(
                DelegatedAccess.invited_phone_e164 == auth.user.phone_e164,
                DelegatedAccess.status == DelegationStatus.INVITED,
            )
            .order_by(DelegatedAccess.invited_at.desc())
        )
    ).all()
    out = []
    for row, profile in rows:
        inviter = await db.get(User, row.invited_by_user_id) if row.invited_by_user_id else None
        out.append(
            InvitationOut(
                id=row.public_id,
                kind=DelegationKind(row.kind),
                relationship=row.relationship,
                subject_name=profile.subject_name,
                profile_display_name=profile.display_name,
                proposed_scopes=[Scope(s) for s in row.permission_scope],
                invited_by_phone_masked=mask_phone(inviter.phone_e164) if inviter else None,
                invited_at=row.invited_at,
            )
        )
    return out


@router.post("/delegations/{delegation_id}/accept")
async def accept_invitation(
    delegation_id: uuid.UUID, body: AcceptIn, auth: Auth, db: DB, meta: Meta
) -> dict[str, str]:
    row = await service.invitation_for(db, auth.user, delegation_id)
    scopes = [s.value for s in body.scopes] if body.scopes is not None else None
    profile = await service.accept(db, auth.user, row, scopes, meta)
    return {"profile_id": str(profile.public_id)}


@router.post("/delegations/{delegation_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_invitation(delegation_id: uuid.UUID, auth: Auth, db: DB, meta: Meta) -> None:
    row = await service.invitation_for(db, auth.user, delegation_id)
    await service.decline(db, auth.user, row, meta)


@router.get("/profiles/{profile_id}/delegates", response_model=list[DelegateSummary])
async def list_delegates(profile_id: uuid.UUID, auth: Auth, db: DB) -> list[DelegateSummary]:
    managed = await load_managed(db, auth.user, profile_id)
    rows = await db.scalars(
        select(DelegatedAccess)
        .where(
            DelegatedAccess.profile_id == managed.profile.id,
            DelegatedAccess.status.in_([DelegationStatus.INVITED, DelegationStatus.ACTIVE]),
        )
        .order_by(DelegatedAccess.id)
    )
    return [await _summary(db, r, auth.user) for r in rows]


@router.post(
    "/profiles/{profile_id}/delegates",
    response_model=DelegateSummary,
    status_code=status.HTTP_201_CREATED,
)
async def invite_helper(
    profile_id: uuid.UUID, body: HelperInviteIn, auth: Auth, db: DB, meta: Meta
) -> DelegateSummary:
    managed = await load_managed(db, auth.user, profile_id, for_update=True)
    managed.require_owner()
    row = await service.invite_helper(
        db,
        managed.profile,
        auth.user,
        normalize_phone(body.phone),
        body.relationship.value,
        [s.value for s in body.scopes],
        meta,
    )
    return await _summary(db, row, auth.user)


async def _owned_delegation(
    db: DB, user: User, delegation_id: uuid.UUID
) -> tuple[DelegatedAccess, Profile]:
    row = await db.scalar(
        select(DelegatedAccess)
        .where(
            DelegatedAccess.public_id == delegation_id,
            DelegatedAccess.status.in_([DelegationStatus.INVITED, DelegationStatus.ACTIVE]),
        )
        .with_for_update()
    )
    if row is None:
        raise NotFound()
    profile = await db.get(Profile, row.profile_id)
    if profile is None:
        raise NotFound()
    related = (
        profile.owner_user_id == user.id
        or row.delegate_user_id == user.id
        or row.invited_by_user_id == user.id
    )
    if not related:
        raise NotFound()
    return row, profile


@router.patch("/delegates/{delegation_id}", response_model=DelegateSummary)
async def update_scopes(
    delegation_id: uuid.UUID, body: ScopesIn, auth: Auth, db: DB, meta: Meta
) -> DelegateSummary:
    row, profile = await _owned_delegation(db, auth.user, delegation_id)
    managed = await load_managed(db, auth.user, profile.public_id)
    managed.require_owner()
    row.permission_scope = [s.value for s in body.scopes]
    from app.audit import service as audit

    await audit.record(
        db,
        action="delegation.scopes",
        resource_type="profile",
        resource_id=str(profile.public_id),
        actor_user_id=auth.user.id,
        after={"delegation": str(row.public_id), "scopes": row.permission_scope},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    return await _summary(db, row, auth.user)


@router.delete("/delegates/{delegation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke(delegation_id: uuid.UUID, auth: Auth, db: DB, meta: Meta) -> None:
    row, profile = await _owned_delegation(db, auth.user, delegation_id)
    await service.revoke(db, auth.user, row, profile, meta)
