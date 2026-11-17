"""Profile and photo moderation (PRD §6.1, §9). The admin portal UI arrives in Phase 5."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.audit import service as audit
from app.common.errors import AppError, NotFound, PermissionDenied
from app.common.phone import mask_phone
from app.delegation.models import DelegatedAccess, DelegationStatus
from app.media.models import ProfilePhoto
from app.profiles import service as profiles
from app.profiles.access import Managed, ManagerRole
from app.profiles.models import Profile, ProfileStatusHistory
from app.profiles.options import ModerationStatus, ProfileStatus, ReviewReason
from app.profiles.schemas import ProfileManageOut
from app.security.deps import DB, AuthContext, Meta, require_roles
from app.security.roles import RoleCode
from app.users.models import User

router = APIRouter(prefix="/admin", tags=["admin", "moderation"])

Moderator = Annotated[
    AuthContext, Depends(require_roles(RoleCode.MODERATOR, RoleCode.OPERATIONS_ADMIN))
]


class QueueItem(BaseModel):
    id: uuid.UUID
    display_name: str | None
    created_for: str
    status: ProfileStatus
    status_reason_code: str | None
    completion_percent: int
    pending_photos: int
    submitted_at: datetime | None


class QueuePage(BaseModel):
    items: list[QueueItem]
    next_cursor: int | None
    total: int


class HistoryOut(BaseModel):
    from_status: str | None
    to_status: str
    reason_code: str | None
    note: str | None
    created_at: datetime


class AdminProfileOut(BaseModel):
    profile: ProfileManageOut
    owner_phone_masked: str | None
    helper_count: int
    history: list[HistoryOut]


class ProfileDecisionIn(BaseModel):
    decision: Literal["approve", "request_changes"]
    reason_code: ReviewReason | None = None
    note: str | None = Field(default=None, max_length=500)
    # Optional photo decisions applied in the same review.
    photos: dict[uuid.UUID, Literal["approve", "reject"]] = Field(default_factory=dict)


class PhotoDecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    reason_code: ReviewReason | None = None


async def _is_own(db: DB, staff: User, profile: Profile) -> bool:
    """Staff may not review a profile they own or help manage (conflict of interest)."""
    if profile.owner_user_id == staff.id or profile.created_by_user_id == staff.id:
        return True
    return (
        await db.scalar(
            select(DelegatedAccess.id).where(
                DelegatedAccess.profile_id == profile.id,
                DelegatedAccess.delegate_user_id == staff.id,
                DelegatedAccess.status == DelegationStatus.ACTIVE,
            )
        )
        is not None
    )


async def _load(db: DB, profile_id: uuid.UUID, *, for_update: bool = False) -> Profile:
    stmt = select(Profile).where(Profile.public_id == profile_id)
    if for_update:
        stmt = stmt.with_for_update()
    profile = await db.scalar(stmt)
    if profile is None:
        raise NotFound()
    return profile


@router.get("/profiles", response_model=QueuePage)
async def queue(
    _: Moderator,
    db: DB,
    status: ProfileStatus = ProfileStatus.SUBMITTED,
    cursor: Annotated[int | None, Query(description="Return items after this id")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> QueuePage:
    """Review queue, oldest submission first."""
    pending = (
        select(func.count())
        .select_from(ProfilePhoto)
        .where(
            ProfilePhoto.profile_id == Profile.id,
            ProfilePhoto.deleted_at.is_(None),
            ProfilePhoto.moderation_status == ModerationStatus.PENDING,
        )
        .scalar_subquery()
    )
    stmt = (
        select(Profile, pending)
        .where(Profile.profile_status == status.value, Profile.owner_user_id.is_not(None))
        .order_by(Profile.submitted_at, Profile.id)
        .limit(limit + 1)
    )
    if cursor is not None:
        stmt = stmt.where(Profile.id > cursor)
    rows = (await db.execute(stmt)).all()
    total = await db.scalar(
        select(func.count())
        .select_from(Profile)
        .where(Profile.profile_status == status.value, Profile.owner_user_id.is_not(None))
    )
    page = rows[:limit]
    return QueuePage(
        items=[
            QueueItem(
                id=p.public_id,
                display_name=p.display_name,
                created_for=p.created_for,
                status=ProfileStatus(p.profile_status),
                status_reason_code=p.status_reason_code,
                completion_percent=p.completion_percent,
                pending_photos=int(n or 0),
                submitted_at=p.submitted_at,
            )
            for p, n in page
        ],
        next_cursor=page[-1][0].id if len(rows) > limit and page else None,
        total=int(total or 0),
    )


@router.get("/profiles/{profile_id}", response_model=AdminProfileOut)
async def review_detail(
    profile_id: uuid.UUID, auth: Moderator, db: DB, meta: Meta
) -> AdminProfileOut:
    profile = await _load(db, profile_id)
    owner = await db.get(User, profile.owner_user_id) if profile.owner_user_id else None
    helpers = await db.scalar(
        select(func.count())
        .select_from(DelegatedAccess)
        .where(
            DelegatedAccess.profile_id == profile.id,
            DelegatedAccess.status == DelegationStatus.ACTIVE,
        )
    )
    history = await db.scalars(
        select(ProfileStatusHistory)
        .where(ProfileStatusHistory.profile_id == profile.id)
        .order_by(ProfileStatusHistory.id.desc())
        .limit(50)
    )
    # Viewing personal data for moderation is itself audited (PRD §10.4).
    await audit.record(
        db,
        action="moderation.view",
        resource_type="profile",
        resource_id=str(profile.public_id),
        actor_user_id=auth.user.id,
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    return AdminProfileOut(
        profile=await profiles.manage_out(db, Managed(profile, ManagerRole.STAFF)),
        owner_phone_masked=mask_phone(owner.phone_e164) if owner else None,
        helper_count=int(helpers or 0),
        history=[
            HistoryOut(
                from_status=h.from_status,
                to_status=h.to_status,
                reason_code=h.reason_code,
                note=h.note,
                created_at=h.created_at,
            )
            for h in history
        ],
    )


async def _decide_photo(
    db: DB, photo: ProfilePhoto, decision: str, reason: str | None, staff: User, meta: Meta
) -> None:
    before = photo.moderation_status
    photo.moderation_status = (
        ModerationStatus.APPROVED if decision == "approve" else ModerationStatus.REJECTED
    )
    photo.moderation_reason = reason if decision == "reject" else None
    if decision == "reject" and photo.is_primary:
        photo.is_primary = False
        others = [
            p
            for p in await profiles.active_photos(db, photo.profile_id)
            if p.id != photo.id and p.moderation_status != ModerationStatus.REJECTED
        ]
        if others:
            others[0].is_primary = True
    await audit.record(
        db,
        action=f"moderation.photo.{decision}",
        resource_type="profile_photo",
        resource_id=str(photo.public_id),
        actor_user_id=staff.id,
        before={"moderation_status": before},
        after={"moderation_status": photo.moderation_status, "reason": reason},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )


@router.post("/profiles/{profile_id}/decision", response_model=AdminProfileOut)
async def decide_profile(
    profile_id: uuid.UUID, body: ProfileDecisionIn, auth: Moderator, db: DB, meta: Meta
) -> AdminProfileOut:
    profile = await _load(db, profile_id, for_update=True)
    if await _is_own(db, auth.user, profile):
        raise PermissionDenied(
            "You can't review a profile you manage.", code="conflict_of_interest"
        )
    if profile.profile_status != ProfileStatus.SUBMITTED:
        raise AppError(
            "Only submitted profiles can be reviewed.", code="invalid_transition", status_code=409
        )

    photos = {p.public_id: p for p in await profiles.active_photos(db, profile.id)}
    unknown = set(body.photos) - set(photos)
    if unknown:
        raise NotFound("Unknown photo.")
    for pid, decision in body.photos.items():
        reason = ReviewReason.PHOTO_UNCLEAR.value if decision == "reject" else None
        await _decide_photo(db, photos[pid], decision, reason, auth.user, meta)

    if body.decision == "approve":
        if not any(p.moderation_status == ModerationStatus.APPROVED for p in photos.values()):
            raise AppError(
                "Approve at least one photo before approving the profile.",
                code="no_approved_photo",
                status_code=422,
            )
        await profiles.transition(
            db,
            profile,
            ProfileStatus.APPROVED,
            by="moderator",
            actor=auth.user,
            meta=meta,
            note=body.note,
        )
    else:
        if body.reason_code is None:
            raise AppError(
                "Choose a reason so the member knows what to change.",
                code="reason_required",
                status_code=422,
            )
        await profiles.transition(
            db,
            profile,
            ProfileStatus.NEEDS_CHANGES,
            by="moderator",
            actor=auth.user,
            meta=meta,
            reason_code=body.reason_code.value,
            note=body.note,
        )
    await db.flush()
    return await review_detail(profile_id, auth, db, meta)


@router.post("/photos/{photo_id}/decision", status_code=204)
async def decide_photo(
    photo_id: uuid.UUID, body: PhotoDecisionIn, auth: Moderator, db: DB, meta: Meta
) -> None:
    photo = await db.scalar(
        select(ProfilePhoto)
        .where(ProfilePhoto.public_id == photo_id, ProfilePhoto.deleted_at.is_(None))
        .with_for_update()
    )
    if photo is None:
        raise NotFound()
    profile = await db.get(Profile, photo.profile_id)
    if profile is None:
        raise NotFound()
    if await _is_own(db, auth.user, profile):
        raise PermissionDenied(
            "You can't review a profile you manage.", code="conflict_of_interest"
        )
    if body.decision == "reject" and body.reason_code is None:
        raise AppError("Choose a reason.", code="reason_required", status_code=422)
    await _decide_photo(
        db,
        photo,
        body.decision,
        body.reason_code.value if body.reason_code else None,
        auth.user,
        meta,
    )
